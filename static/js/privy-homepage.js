import React, { useCallback, useState } from "https://esm.sh/react@19.2.7";
import { createRoot } from "https://esm.sh/react-dom@19.2.7/client";
import {
    PrivyProvider,
    useLogin,
    useWallets,
    usePrivy,
} from "https://esm.sh/@privy-io/react-auth@3.29.2?deps=react@19.2.7,react-dom@19.2.7";

const h = React.createElement;

function readBootstrap() {
    const node = document.getElementById("privyHomepageBootstrap");
    if (!node) return {};
    try {
        return JSON.parse(node.textContent || "{}");
    } catch (err) {
        console.error("[GoodMarket Privy] Invalid bootstrap JSON", err);
        return {};
    }
}

function statusColor(kind) {
    if (kind === "success") return "#10b981";
    if (kind === "warning") return "#f59e0b";
    if (kind === "error") return "#ef4444";
    return "#6b7280";
}

function PrivyActions() {
    const { ready, authenticated } = usePrivy();
    const { wallets } = useWallets();
    const [busy, setBusy] = useState(false);
    const [pendingLogin, setPendingLogin] = useState(false);
    const [status, setStatus] = useState({
        kind: "info",
        text: "Sign in with Privy social login to continue.",
    });

    const signAndVerify = useCallback(async (wallet, label) => {
        const provider = await wallet.getEthereumProvider();
        const address = wallet.address;
        const message = window.makeLoginMessage(address);
        const messageHex = window.utf8ToHex(message);
        setStatus({ kind: "info", text: `Signing ${label} message in Privy…` });
        const signature = await provider.request({
            method: "personal_sign",
            params: [messageHex, address],
        });
        const verifyData = await window.postVerifyIdentity(
            address,
            signature,
            message,
            window.getPendingReferralCode(),
            "privy",
        );
        const warned = Boolean(verifyData && verifyData.referral_warning);
        setStatus({
            kind: warned ? "warning" : "success",
            text: warned
                ? `✅ ${label} complete. ⚠️ ${verifyData.referral_warning} Redirecting…`
                : `✅ ${label} complete. Redirecting…`,
        });
        window.setTimeout(() => {
            window.location.href = "/wallet";
        }, warned ? 2400 : 900);
    }, []);

    const { login } = useLogin({
        onError: (error) => {
            const message = error && error.message ? error.message : "Privy social login failed";
            setPendingLogin(false);
            setBusy(false);
            setStatus({ kind: "error", text: message });
        },
    });

    const runLogin = useCallback(async () => {
        if (!ready) {
            setStatus({ kind: "warning", text: "Privy is still loading." });
            return;
        }
        setBusy(true);
        setPendingLogin(true);
        try {
            setStatus({ kind: "info", text: "Opening Privy social login…" });
            await login();
        } catch (err) {
            const message = err && err.message ? err.message : "Privy social login failed";
            setStatus({ kind: "error", text: message });
            setPendingLogin(false);
            setBusy(false);
        }
    }, [login, ready]);

    const walletList = Array.isArray(wallets) ? wallets : [];
    const selectedWallet = walletList.find((wallet) => wallet && wallet.walletClientType === "privy" && wallet.chainType === "ethereum")
        || walletList.find((wallet) => wallet && wallet.walletClientType === "privy")
        || walletList[0]
        || null;

    React.useEffect(() => {
        if (!pendingLogin || !ready || !authenticated || !selectedWallet) return;
        let cancelled = false;
        (async () => {
            try {
                setPendingLogin(false);
                await signAndVerify(selectedWallet, "Social login");
            } catch (err) {
                if (cancelled) return;
                const message = err && err.message ? err.message : "Privy sign-in failed";
                setStatus({ kind: "error", text: message });
                setBusy(false);
                setPendingLogin(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [authenticated, pendingLogin, ready, selectedWallet, signAndVerify]);

    return h(
        "div",
        {
            style: {
                marginTop: "0.75rem",
                padding: "1rem",
                borderRadius: "16px",
                border: "1px solid rgba(124, 58, 237, 0.18)",
                background: "linear-gradient(180deg, rgba(124, 58, 237, 0.08), rgba(255,255,255,0.96))",
            },
        },
        h(
            "div",
            { style: { display: "flex", flexDirection: "column", gap: "0.25rem", marginBottom: "0.75rem" } },
            h("div", { style: { fontSize: "0.98rem", fontWeight: "800", color: "#1f2937" } }, "Privy social login"),
            h(
                "div",
                { style: { fontSize: "0.78rem", color: "#6b7280", lineHeight: "1.45" } },
                "Open Privy's login modal, then sign in with Google or another configured method."
            )
        ),
        h(
            "button",
            {
                type: "button",
                disabled: busy || !ready,
                onClick: runLogin,
                style: {
                    width: "100%",
                    border: "none",
                    borderRadius: "12px",
                    padding: "0.9rem 1rem",
                    background: "linear-gradient(135deg, #7c3aed, #4f46e5)",
                    color: "white",
                    fontWeight: "800",
                    cursor: busy || !ready ? "not-allowed" : "pointer",
                    opacity: busy || !ready ? 0.72 : 1,
                },
            },
            busy ? "Opening…" : "Social Login"
        ),
        h(
            "button",
            {
                type: "button",
                onClick: () => {
                    if (typeof window.showWalletConnectOptions === "function") {
                        window.showWalletConnectOptions();
                    }
                },
                style: {
                    marginTop: "0.65rem",
                    background: "transparent",
                    border: "none",
                    color: "#6d28d9",
                    fontWeight: "700",
                    cursor: "pointer",
                    padding: 0,
                },
            },
            "Use the existing WalletConnect flow"
        ),
        h(
            "p",
            {
                style: {
                    marginTop: "0.65rem",
                    marginBottom: 0,
                    fontSize: "0.76rem",
                    color: statusColor(status.kind),
                    lineHeight: "1.45",
                },
            },
            status.text
        )
    );
}

function App({ appId }) {
    if (!appId) {
        return h(
            "div",
            {
                style: {
                    marginTop: "0.75rem",
                    padding: "0.9rem 1rem",
                    borderRadius: "14px",
                    background: "rgba(239, 68, 68, 0.08)",
                    color: "#b91c1c",
                    fontSize: "0.8rem",
                    lineHeight: "1.45",
                },
            },
            "Set PRIVY_APP_ID to enable the embedded wallet buttons."
        );
    }

    return h(
        PrivyProvider,
        {
            appId,
            config: {
                appearance: {
                    showWalletLoginFirst: false,
                },
                embeddedWallets: {
                    ethereum: {
                        createOnLogin: "users-without-wallets",
                    },
                },
            },
        },
        h(PrivyActions)
    );
}

function mount() {
    const rootEl = document.getElementById("privyWalletRoot");
    if (!rootEl) return;
    const bootstrap = readBootstrap();
    const appId = String(bootstrap.appId || "").trim();
    createRoot(rootEl).render(h(App, { appId }));
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount, { once: true });
} else {
    mount();
}
