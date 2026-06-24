#!/usr/bin/env python3
"""
Fix orphaned trades in P2P Escrow.

This script finds and expires trades that exist on-chain but not in the database.
Run this when an ad has activeTradeCount > 0 but no corresponding trade in DB.

Usage:
    python scripts/fix_orphaned_trade.py <order_id>
    python scripts/fix_orphaned_trade.py P2P-73533C0D
"""

import sys
import os
import json
import logging
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from eth_abi import decode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Contract config
CONTRACT_ADDR = "0x2B9FA9b85BBB44b8FCBa550b6C9cA8792ce00f03"
RPC_URL = os.getenv("CELO_RPC_URL", "https://forno.celo.org")

def get_contract_abi():
    """Load contract ABI from deployment file."""
    deployment_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "contracts",
        "p2p_escrow_deployment.json"
    )
    with open(deployment_path) as f:
        return json.load(f)["abi"]

def find_ad_trade_ids(web3, contract, ad_id: str) -> list:
    """Find all trade IDs associated with an ad by querying OrderPlaced events."""
    
    # Event selector for OrderPlaced
    # event OrderPlaced(bytes32 indexed tradeId, bytes32 indexed adId, address indexed buyer, uint256 amount, uint64 deadline)
    order_placed_selector = Web3.keccak(text="OrderPlaced(bytes32,bytes32,address,uint256,uint64)").hex()[:10]
    
    ad_id_padded = ad_id[2:].zfill(64) if ad_id.startswith("0x") else ad_id.zfill(64)
    
    trade_ids = []
    
    # Get logs with topic filter for the adId
    # topics[0] = event signature
    # topics[2] = indexed adId
    try:
        logs = web3.eth.get_logs({
            "fromBlock": 0,  # Start from beginning
            "toBlock": "latest",
            "address": CONTRACT_ADDR,
            "topics": [
                "0x" + order_placed_selector[2:].zfill(64),  # Event signature
                None,  # tradeId (indexed, don't filter)
                "0x" + ad_id_padded  # adId (indexed)
            ]
        })
        
        for log in logs:
            # Decode the tradeId from topics[1]
            trade_id = "0x" + log.topics[1].hex()
            trade_ids.append(trade_id)
            logger.info(f"Found trade: {trade_id}")
            
    except Exception as e:
        logger.warning(f"Error fetching logs: {e}")
        # Try alternative: query all OrderPlaced events and filter
        all_logs_selector = "0x" + order_placed_selector[2:].zfill(64)
        try:
            logs = web3.eth.get_logs({
                "fromBlock": 0,
                "toBlock": "latest",
                "address": CONTRACT_ADDR,
                "topics": [all_logs_selector]
            })
            
            for log in logs:
                if len(log.topics) >= 3:
                    topic_ad_id = "0x" + log.topics[2].hex()
                    if topic_ad_id.lower() == ("0x" + ad_id_padded).lower():
                        trade_id = "0x" + log.topics[1].hex()
                        if trade_id not in trade_ids:
                            trade_ids.append(trade_id)
                            logger.info(f"Found trade via filtering: {trade_id}")
                            
        except Exception as e2:
            logger.error(f"Alternative fetch also failed: {e2}")
    
    return trade_ids

def get_trade_status(web3, contract, trade_id: str) -> dict:
    """Get the status of a trade from the contract."""
    
    # getTrade selector
    selector = Web3.keccak(text="getTrade(bytes32)")[:4].hex()
    data = selector + trade_id[2:].zfill(64)
    
    try:
        result = web3.eth.call({
            "to": CONTRACT_ADDR,
            "data": data
        })
        
        if not result or result == b'\x00' * 32:
            return {"exists": False}
        
        # Decode: (adId, buyer, amount, deadline, markedPaidAt, status)
        decoded = decode(
            ['bytes32', 'address', 'uint256', 'uint64', 'uint64', 'uint8'],
            result
        )
        
        status_names = {
            0: "None",
            1: "PaymentPending",
            2: "AwaitingRelease",
            3: "Completed",
            4: "Cancelled",
            5: "Expired",
            6: "Disputed",
            7: "Refunded"
        }
        
        return {
            "exists": True,
            "trade_id": trade_id,
            "ad_id": "0x" + decoded[0].hex(),
            "buyer": decoded[1],
            "amount_wei": decoded[2],
            "amount_gd": web3.from_wei(decoded[2], 'ether'),
            "deadline": decoded[3],
            "marked_paid_at": decoded[4],
            "status_code": decoded[5],
            "status_name": status_names.get(decoded[5], f"Unknown({decoded[5]})")
        }
        
    except Exception as e:
        logger.error(f"Error getting trade status: {e}")
        return {"exists": False, "error": str(e)}

def get_ad_status(web3, contract, ad_id: str) -> dict:
    """Get the status of an ad from the contract."""
    
    selector = Web3.keccak(text="getAd(bytes32)")[:4].hex()
    data = selector + ad_id[2:].zfill(64)
    
    try:
        result = web3.eth.call({
            "to": CONTRACT_ADDR,
            "data": data
        })
        
        if not result:
            return {"exists": False}
        
        decoded = decode(
            ['address', 'uint256', 'uint256', 'uint256', 'uint256', 'uint32', 'bool'],
            result
        )
        
        return {
            "exists": True,
            "ad_id": ad_id,
            "seller": decoded[0],
            "total_locked": web3.from_wei(decoded[1], 'ether'),
            "remaining_amount": web3.from_wei(decoded[2], 'ether'),
            "min_order": web3.from_wei(decoded[3], 'ether'),
            "max_order": web3.from_wei(decoded[4], 'ether'),
            "active_trade_count": decoded[5],
            "open": decoded[6]
        }
        
    except Exception as e:
        logger.error(f"Error getting ad status: {e}")
        return {"exists": False, "error": str(e)}

def check_and_report_issue(ad_id: str, db):
    """
    Check if there's an orphaned trade and report it.
    This doesn't fix anything - just identifies the issue.
    """
    import requests
    
    # Check DB for trades
    result = db.table("p2p_trades").select("*").eq("order_id", ad_id).execute()
    db_trades = result.data
    
    # Query blockchain for trades
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        logger.error("Cannot connect to Celo network")
        return
    
    contract = w3.eth.contract(address=CONTRACT_ADDR, abi=get_contract_abi())
    
    ad_status = get_ad_status(w3, contract, ad_id)
    logger.info(f"Ad on-chain status: {json.dumps(ad_status, indent=2)}")
    
    # Find trades from events
    trade_ids = find_ad_trade_ids(w3, contract, ad_id)
    logger.info(f"Found {len(trade_ids)} trade(s) on-chain for ad {ad_id}")
    
    for trade_id in trade_ids:
        trade_status = get_trade_status(w3, contract, trade_id)
        logger.info(f"Trade {trade_id}: {json.dumps(trade_status, indent=2)}")
        
        # Check if trade exists in DB
        db_trade = next((t for t in db_trades if t.get("trade_id_onchain", "").lower() == trade_id.lower()), None)
        
        if db_trade:
            logger.info(f"Trade EXISTS in DB: {db_trade.get('trade_id')}")
        else:
            logger.warning(f"⚠️ ORPHANED TRADE: {trade_id} - exists on-chain but NOT in database!")
            
            # Check if deadline has passed
            if trade_status.get("status_code") == 1:  # PaymentPending
                deadline = trade_status.get("deadline", 0)
                now = datetime.now(timezone.utc).timestamp()
                if now > deadline:
                    logger.info(f"   → Deadline EXPIRED! Can call expirePendingOrder()")
                    return {
                        "can_fix": True,
                        "trade_id": trade_id,
                        "reason": "Trade is PaymentPending and deadline has passed"
                    }
                else:
                    logger.info(f"   → Deadline: {datetime.fromtimestamp(deadline, tz=timezone.utc)}")
                    return {
                        "can_fix": False,
                        "trade_id": trade_id,
                        "reason": f"Trade is PaymentPending but deadline not yet passed"
                    }
    
    # Check if ad has active trades but no valid on-chain trades
    if ad_status.get("active_trade_count", 0) > 0 and len(trade_ids) == 0:
        logger.error(f"⚠️ STUCK AD: activeTradeCount={ad_status['active_trade_count']} but no trades found!")
        return {
            "can_fix": False,
            "reason": "Ad has activeTradeCount > 0 but no trades found on-chain. Manual intervention needed."
        }
    
    return {"can_fix": False, "reason": "No orphaned trades found"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/fix_orphaned_trade.py <order_id>")
        print("Example: python scripts/fix_orphaned_trade.py P2P-73533C0D")
        sys.exit(1)
    
    order_id = sys.argv[1]
    
    # Try to connect to DB
    try:
        from supabase_client import get_supabase_client
        db = get_supabase_client()
        
        if db:
            result = check_and_report_issue(order_id, db)
            print(json.dumps(result, indent=2, default=str))
        else:
            print("Supabase not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY")
            
    except ImportError:
        print("Supabase client not available")
