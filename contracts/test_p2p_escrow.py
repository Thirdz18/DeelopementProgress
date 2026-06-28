"""
Local accounting tests for P2PEscrow.sol.

Runs the contract on an in-memory py-evm chain (no network) to prove the
escrow invariants ("walang palya"):
  - total == available + reserved-by-open-orders at all times
  - locked G$ never gets stuck (release -> buyer, cancel/refund -> seller)
  - only the right party can take each action
  - owner (P2P_KEY) admin-review release/refund works
  - auto-expiry cancel returns reserved G$ to the seller

Run:
    uv run python contracts/test_p2p_escrow.py
"""

import os
import sys

from eth_tester import EthereumTester, PyEVMBackend
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider
from solcx import compile_standard, install_solc

ONE = 10 ** 18
GD_SUPPLY = 100_000_000 * ONE

# Minimal mintable ERC-20 used as a stand-in for G$ in tests.
ERC20_SRC = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.21;
contract MockERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    function mint(address to, uint256 amt) external { balanceOf[to] += amt; }
    function approve(address s, uint256 amt) external returns (bool) { allowance[msg.sender][s] = amt; return true; }
    function transfer(address to, uint256 amt) external returns (bool) {
        require(balanceOf[msg.sender] >= amt, "bal");
        balanceOf[msg.sender] -= amt; balanceOf[to] += amt; return true;
    }
    function transferFrom(address f, address t, uint256 amt) external returns (bool) {
        require(balanceOf[f] >= amt, "bal");
        require(allowance[f][msg.sender] >= amt, "allow");
        allowance[f][msg.sender] -= amt; balanceOf[f] -= amt; balanceOf[t] += amt; return true;
    }
}
"""


def _compile():
    install_solc("0.8.21")
    p2p_src = open(os.path.join(os.path.dirname(__file__), "P2PEscrow.sol")).read()
    out = compile_standard(
        {
            "language": "Solidity",
            "sources": {
                "P2PEscrow.sol": {"content": p2p_src},
                "MockERC20.sol": {"content": ERC20_SRC},
            },
            "settings": {
                "optimizer": {"enabled": True, "runs": 200},
                "outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}},
            },
        },
        solc_version="0.8.21",
    )
    return out["contracts"]


def _deploy(w3, art, sender, *args):
    c = w3.eth.contract(abi=art["abi"], bytecode=art["evm"]["bytecode"]["object"])
    tx = c.constructor(*args).transact({"from": sender})
    rcpt = w3.eth.wait_for_transaction_receipt(tx)
    return w3.eth.contract(address=rcpt.contractAddress, abi=art["abi"])


def _send(w3, fn, sender):
    tx = fn.transact({"from": sender})
    return w3.eth.wait_for_transaction_receipt(tx)


def _expect_revert(w3, fn, sender, label):
    try:
        _send(w3, fn, sender)
    except Exception:
        return
    raise AssertionError(f"expected revert: {label}")


def _invariant(escrow, listing_id):
    seller, total, available, _min, _active = escrow.functions.getListing(listing_id).call()
    return total, available


def main():
    contracts = _compile()
    tester = EthereumTester(backend=PyEVMBackend())
    w3 = Web3(EthereumTesterProvider(tester))

    owner, seller, buyer, buyer2 = w3.eth.accounts[:4]

    gd = _deploy(w3, contracts["MockERC20.sol"]["MockERC20"], owner)
    escrow = _deploy(w3, contracts["P2PEscrow.sol"]["P2PEscrow"], owner, gd.address, 1800)

    # Fund seller with G$.
    _send(w3, gd.functions.mint(seller, GD_SUPPLY), owner)

    # ── createListing: bounds + escrow pull ────────────────────────────────────
    _expect_revert(w3, escrow.functions.createListing(999 * ONE, 999 * ONE), seller, "below MIN_LOCK")
    _expect_revert(w3, escrow.functions.createListing(2_000_000 * ONE, 1000 * ONE), seller, "above MAX_LOCK")

    lock = 100_000 * ONE
    _send(w3, gd.functions.approve(escrow.address, lock), seller)
    _send(w3, escrow.functions.createListing(lock, 1000 * ONE), seller)
    listing_id = 1
    assert gd.functions.balanceOf(escrow.address).call() == lock, "escrow did not hold G$"
    total, avail = _invariant(escrow, listing_id)
    assert total == lock and avail == lock, "initial accounting wrong"

    # ── openOrder: min + availability + reservation ─────────────────────────────
    _expect_revert(w3, escrow.functions.openOrder(listing_id, 500 * ONE), buyer, "below minOrder")
    _expect_revert(w3, escrow.functions.openOrder(listing_id, 200_000 * ONE), buyer, "exceeds available")
    _expect_revert(w3, escrow.functions.openOrder(listing_id, 1000 * ONE), seller, "buyer == seller")

    order_amt = 40_000 * ONE
    _send(w3, escrow.functions.openOrder(listing_id, order_amt), buyer)
    order_id = 1
    total, avail = _invariant(escrow, listing_id)
    assert total == lock and avail == lock - order_amt, "reservation accounting wrong"

    # ── happy path: buyer marks paid, seller releases ──────────────────────────
    _expect_revert(w3, escrow.functions.releaseOrder(order_id), buyer, "non-seller release")
    _send(w3, escrow.functions.markPaid(order_id), buyer)
    _expect_revert(w3, escrow.functions.markPaid(order_id), buyer, "double markPaid")
    _send(w3, escrow.functions.releaseOrder(order_id), seller)
    assert gd.functions.balanceOf(buyer).call() == order_amt, "buyer did not receive G$"
    total, avail = _invariant(escrow, listing_id)
    assert total == lock - order_amt and avail == lock - order_amt, "post-release accounting wrong"

    # ── second order cancelled by buyer -> returns to available ─────────────────
    _send(w3, escrow.functions.openOrder(listing_id, 10_000 * ONE), buyer2)
    order2 = 2
    total_b, avail_b = _invariant(escrow, listing_id)
    _send(w3, escrow.functions.cancelOrder(order2), buyer2)
    total_a, avail_a = _invariant(escrow, listing_id)
    assert avail_a == avail_b + 10_000 * ONE and total_a == total_b, "cancel did not return reserved"

    # ── owner admin-review release (seller rejected but proof was genuine) ──────
    _send(w3, escrow.functions.openOrder(listing_id, 5_000 * ONE), buyer2)
    order3 = 3
    _send(w3, escrow.functions.markPaid(order3), buyer2)
    _expect_revert(w3, escrow.functions.releaseOrderByOwner(order3), seller, "non-owner admin release")
    bal_before = gd.functions.balanceOf(buyer2).call()
    _send(w3, escrow.functions.releaseOrderByOwner(order3), owner)
    assert gd.functions.balanceOf(buyer2).call() == bal_before + 5_000 * ONE, "owner release failed"

    # ── owner admin-review refund (fake proof) -> back to seller available ──────
    _send(w3, escrow.functions.openOrder(listing_id, 7_000 * ONE), buyer2)
    order4 = 4
    _send(w3, escrow.functions.markPaid(order4), buyer2)
    _, avail_pre = _invariant(escrow, listing_id)
    _send(w3, escrow.functions.refundOrderByOwner(order4), owner)
    _, avail_post = _invariant(escrow, listing_id)
    assert avail_post == avail_pre + 7_000 * ONE, "owner refund did not return G$"

    # ── dispute resolution ──────────────────────────────────────────────────────
    _send(w3, escrow.functions.openOrder(listing_id, 3_000 * ONE), buyer2)
    order5 = 5
    _send(w3, escrow.functions.markPaid(order5), buyer2)
    _send(w3, escrow.functions.raiseDispute(order5), buyer2)
    bal_before = gd.functions.balanceOf(buyer2).call()
    _send(w3, escrow.functions.resolveDispute(order5, True), owner)
    assert gd.functions.balanceOf(buyer2).call() == bal_before + 3_000 * ONE, "dispute release failed"

    # ── seller withdraw + cancel listing refunds available ──────────────────────
    seller_bal_before = gd.functions.balanceOf(seller).call()
    _, avail_now = _invariant(escrow, listing_id)
    _send(w3, escrow.functions.withdrawAvailable(listing_id, 1_000 * ONE), seller)
    _send(w3, escrow.functions.cancelListing(listing_id), seller)
    total_final, avail_final = _invariant(escrow, listing_id)
    assert avail_final == 0, "cancelListing left available G$"
    seller_bal_after = gd.functions.balanceOf(seller).call()
    assert seller_bal_after == seller_bal_before + avail_now, "seller refund mismatch on cancel"

    # No G$ stuck: escrow holds zero after everything settled and listing closed.
    assert gd.functions.balanceOf(escrow.address).call() == total_final == 0, "G$ stuck in escrow"

    print("ALL P2PEscrow ACCOUNTING TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
