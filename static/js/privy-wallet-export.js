import React, { useCallback, useMemo, useState } from "https://esm.sh/react@19.2.7";
import { createRoot } from "https://esm.sh/react-dom@19.2.7/client";
import {
    PrivyProvider,
    useExportWallet,
    usePrivy,
} from "https://esm.sh/@privy-io/react-auth@3.29.2?deps=react@19.2.7,react-dom@19.2.7";

const h = React.createElement;

function readBootstrap() {
    const node = document.getElementById("privyWalletBootstrap");
    if (!node) return {};
    try {
        return JSON.parse(node.textContent || "{}");
    } catch (err) {
        console.error("[GoodMarket Privy] Invalid wallet bootstrap JSON", err);
        return {};
    }
}

function hasEmbeddedEthereumWallet(user) {
    return Boolean(user && Array.isArray(user.linkedAccounts) && user.linkedAccounts.some((account) => (
        account
        && account.type === "wallet"
        && account.walletClientType === "privy"
        && account.chainType === "ethereum"
    )));
}

function ExportWalletButton() {
    const { ready, authenticated, user } = usePrivy();
    const { exportWallet } = useExportWallet();
    const [busy, setBusy] = useState(false);
    const [status, setStatus] = useState("Export private key");

    const enabled = useMemo(() => ready && authenticated && hasEmbeddedEthereumWallet(user), [ready, authenticated, user]);

    const onExport = useCallback(async () => {
        if (!enabled) return;
        setBusy(true);
        setStatus("Opening Privy export modal…");
        try {
            await exportWallet();
            setStatus("Export modal opened.");
        } catch (err) {
            const message = err && err.message ? err.message : "Unable to open export modal";
            setStatus(message);
        } finally {
            setBusy(false);
        }
    }, [enabled, exportWallet]);

    return h(
        "div",
        {
            style: {
                display: "flex",
                flexDirection: "column",
                gap: "0.45rem",
            },
        },
        h(
            "button",
            {
                type: "button",
                disabled: !enabled || busy,
                onClick: onExport,
                style: {
                    width: "100%",
                    border: "none",
                    borderRadius: "12px",
                    padding: "0.8rem 0.9rem",
                    background: enabled && !busy ? "linear-gradient(135deg, #7c3aed, #4f46e5)" : "rgba(255,255,255,0.08)",
                    color: "#fff",
                    fontWeight: "800",
                    cursor: enabled && !busy ? "pointer" : "not-allowed",
                    opacity: enabled && !busy ? 1 : 0.7,
                },
            },
            busy ? "Opening…" : "Export Private Key"
        ),
        h(
            "div",
            {
                style: {
                    fontSize: "0.76rem",
                    lineHeight: "1.45",
                    color: enabled ? "#c4b5fd" : "#9ca3af",
                },
            },
            enabled
                ? "Privy users can export their embedded wallet key here."
                : "This option only appears for authenticated Privy embedded-wallet users."
        ),
        h(
            "div",
            {
                style: {
                    fontSize: "0.74rem",
                    lineHeight: "1.4",
                    color: "#94a3b8",
                },
            },
            status
        )
    );
}

function App({ appId }) {
    if (!appId) {
        return h(
            "div",
            {
                style: {
                    fontSize: "0.78rem",
                    lineHeight: "1.5",
                    color: "#fca5a5",
                },
            },
            "Set PRIVY_APP_ID to enable Privy wallet export."
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
        h(ExportWalletButton)
    );
}

function mount() {
    const rootEl = document.getElementById("privyExportWalletRoot");
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
