import React, { useCallback, useState } from "https://esm.sh/react@19.2.7";
import { createRoot } from "https://esm.sh/react-dom@19.2.7/client";
import {
    PrivyProvider,
    useConnectOrCreateWallet,
    useCreateWallet,
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
    const { ready } = usePrivy();
    const [busy, setBusy] = useState(false);
    const [status, setStatus] = useState({
        kind: "info",
        text: "Use Privy to create a fresh embedded wallet.",
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

    const { connectOrCreateWallet } = useConnectOrCreateWallet({
        onSuccess: async ({ wallet }) => {
            try {
                await signAndVerify(wallet, "Privy wallet");
            } catch (err) {
                const message = err && err.message ? err.message : "Privy connect failed";
                setBusy(false);
                setStatus({ kind: "error", text: message });
            }
        },
        onError: (error) => {
            const message = error && error.message ? error.message : "Privy connect failed";
            setBusy(false);
            setStatus({ kind: "error", text: message });
        },
    });
    const { createWallet } = useCreateWallet();

    const runConnect = useCallback(async () => {
        if (!ready) {
            setStatus({ kind: "warning", text: "Privy is still loading." });
            return;
        }
        setBusy(true);
        try {
            setStatus({ kind: "info", text: "Opening Privy to connect a wallet…" });
            await connectOrCreateWallet();
        } catch (err) {
            const message = err && err.message ? err.message : "Privy connect failed";
            setStatus({ kind: "error", text: message });
            setBusy(false);
        }
    }, [connectOrCreateWallet, ready]);

    const runCreate = useCallback(async () => {
        if (!ready) {
            setStatus({ kind: "warning", text: "Privy is still loading." });
            return;
        }
        setBusy(true);
        try {
            setStatus({ kind: "info", text: "Creating a new embedded wallet…" });
            const wallet = await createWallet({ createAdditional: false });
            await signAndVerify(wallet, "embedded wallet");
        } catch (err) {
            const message = err && err.message ? err.message : "Privy wallet creation failed";
            setStatus({ kind: "error", text: message });
        } finally {
            setBusy(false);
        }
    }, [createWallet, ready, signAndVerify]);

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
            h("div", { style: { fontSize: "0.98rem", fontWeight: "800", color: "#1f2937" } }, "Privy embedded wallet"),
            h(
                "div",
                { style: { fontSize: "0.78rem", color: "#6b7280", lineHeight: "1.45" } },
                "Connect an existing wallet or create a fresh embedded wallet with your Privy app."
            )
        ),
        h(
            "div",
            {
                style: {
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: "0.6rem",
                },
            },
            h(
                "button",
                {
                    type: "button",
                    disabled: busy || !ready,
                    onClick: runConnect,
                    style: {
                        border: "none",
                        borderRadius: "12px",
                        padding: "0.8rem 0.9rem",
                        background: "linear-gradient(135deg, #7c3aed, #4f46e5)",
                        color: "white",
                        fontWeight: "800",
                        cursor: busy || !ready ? "not-allowed" : "pointer",
                        opacity: busy || !ready ? 0.72 : 1,
                    },
                },
                busy ? "Opening…" : "Connect with Privy"
            ),
            h(
                "button",
                {
                    type: "button",
                    disabled: busy || !ready,
                    onClick: runCreate,
                    style: {
                        border: "none",
                        borderRadius: "12px",
                        padding: "0.8rem 0.9rem",
                        background: "linear-gradient(135deg, #10b981, #059669)",
                        color: "white",
                        fontWeight: "800",
                        cursor: busy || !ready ? "not-allowed" : "pointer",
                        opacity: busy || !ready ? 0.72 : 1,
                    },
                },
                busy ? "Opening…" : "Create New Wallet"
            )
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
