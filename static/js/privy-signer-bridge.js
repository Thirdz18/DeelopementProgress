import React, { useEffect, useMemo } from "https://esm.sh/react@19.2.7";
import { createRoot } from "https://esm.sh/react-dom@19.2.7/client";
import {
    PrivyProvider,
    usePrivy,
    useWallets,
} from "https://esm.sh/@privy-io/react-auth@3.29.2?deps=react@19.2.7,react-dom@19.2.7";

const h = React.createElement;

function readBootstrap() {
    const node = document.getElementById("privySignerBootstrap");
    if (!node) return {};
    try {
        return JSON.parse(node.textContent || "{}");
    } catch (err) {
        console.error("[GoodMarket Privy] Invalid signer bootstrap JSON", err);
        return {};
    }
}

function selectWallet(wallets) {
    if (!Array.isArray(wallets) || !wallets.length) return null;
    return (
        wallets.find((wallet) => wallet && wallet.walletClientType === "privy" && wallet.chainType === "ethereum") ||
        wallets.find((wallet) => wallet && wallet.walletClientType === "privy") ||
        wallets[0] ||
        null
    );
}

function installWallet(wallet, provider) {
    window.__privyConnectedWallet = wallet;
    window.__privyEthereumProvider = provider;
    window.__getPrivyEthereumProvider = async () => provider;
    window.dispatchEvent(new CustomEvent("privy:ethereum-provider-ready", {
        detail: { address: wallet && wallet.address ? wallet.address : "" },
    }));
}

function clearWallet() {
    delete window.__privyConnectedWallet;
    delete window.__privyEthereumProvider;
    delete window.__getPrivyEthereumProvider;
}

function SignerBridge() {
    const { ready, authenticated } = usePrivy();
    const { wallets } = useWallets();
    const wallet = useMemo(() => selectWallet(wallets), [wallets]);

    useEffect(() => {
        let cancelled = false;
        if (!ready || !authenticated || !wallet) {
            clearWallet();
            return () => {};
        }
        if (typeof wallet.getEthereumProvider !== "function") {
            clearWallet();
            return () => {};
        }
        (async () => {
            try {
                const provider = await wallet.getEthereumProvider();
                if (!cancelled && provider) {
                    installWallet(wallet, provider);
                }
            } catch (err) {
                if (!cancelled) {
                    console.error("[GoodMarket Privy] Failed to load wallet provider", err);
                    clearWallet();
                }
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [authenticated, ready, wallet]);

    return null;
}

function App({ appId }) {
    if (!appId) return null;
    return h(
        PrivyProvider,
        {
            appId,
            config: {
                embeddedWallets: {
                    ethereum: {
                        createOnLogin: "users-without-wallets",
                    },
                },
            },
        },
        h(SignerBridge)
    );
}

function mount() {
    let rootEl = document.getElementById("privySignerBridgeRoot");
    if (!rootEl) {
        rootEl = document.createElement("div");
        rootEl.id = "privySignerBridgeRoot";
        rootEl.style.display = "none";
        document.body.appendChild(rootEl);
    }
    const bootstrap = readBootstrap();
    const appId = String(bootstrap.appId || "").trim();
    createRoot(rootEl).render(h(App, { appId }));
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount, { once: true });
} else {
    mount();
}
