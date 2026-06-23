/**
 * Privy Embedded Wallet Integration
 * Handles wallet creation via email, Google, phone
 */

let privyProvider = null;
let privyEmbeddedWallet = null;

/**
 * Initialize and show the Privy form
 */
function showPrivyForm() {
    document.getElementById('walletOptions').style.display = 'none';
    document.getElementById('privyFormContainer').classList.add('visible');
    document.getElementById('privySuccessContainer').style.display = 'none';
    initPrivy();
}

/**
 * Initialize Privy embedded wallet
 */
function initPrivy() {
    // Check if already initialized
    if (window.PrivyFirstWalletProvider || privyProvider) {
        console.log('Privy already initialized');
        return;
    }

    const container = document.getElementById('privy-embed-container');
    if (!container) {
        console.error('Privy container not found');
        return;
    }

    // Get App ID from template variable
    const PRIVY_APP_ID = typeof PRIVY_APP_ID_VAR !== 'undefined' ? PRIVY_APP_ID_VAR : '';

    if (!PRIVY_APP_ID) {
        container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #6b7280;">
                <p style="margin-bottom: 1rem;">⚠️ Privy App ID not configured</p>
                <p style="font-size: 0.85rem;">Please set the PRIVY_APP_ID environment variable to enable wallet creation.</p>
                <p style="font-size: 0.75rem; margin-top: 1rem;">Get your App ID at <a href="https://privy.io" target="_blank" style="color: #7c3aed;">privy.io</a></p>
            </div>
        `;
        return;
    }

    try {
        // Initialize Privy embed
        window.PrivyFirstWalletProvider.initEmbedded(PRIVY_APP_ID, {
            container: container,
            embeddedWallets: {
                showWidget: true,
                createOnDemand: true,
                requireUserOwnership: true,
            },
            appearance: {
                theme: 'light',
                accentColor: '#7c3aed',
                logo: 'https://goodmarket.live/static/icons/goodmarket-icon.png',
            },
        }).then((result) => {
            if (result && result.provider) {
                privyProvider = result.provider;
                privyEmbeddedWallet = result;
                console.log('✅ Privy embedded wallet initialized');
                setupPrivyCallbacks();
            }
        }).catch((error) => {
            console.error('❌ Privy init error:', error);
            container.innerHTML = `
                <div style="padding: 2rem; text-align: center; color: #ef4444;">
                    <p>Failed to initialize wallet creator. Please try again.</p>
                </div>
            `;
        });
    } catch (error) {
        console.error('Privy error:', error);
        container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #6b7280;">
                <p>Error loading wallet creator. Please refresh the page.</p>
            </div>
        `;
    }
}

/**
 * Setup Privy event callbacks
 */
function setupPrivyCallbacks() {
    if (window.PrivyFirstWalletProvider) {
        window.PrivyFirstWalletProvider.on('createWallet', async (wallet) => {
            console.log('🎉 New wallet created:', wallet);
            showPrivySuccess(wallet.address);
        });

        window.PrivyFirstWalletProvider.on('linked', async (wallet) => {
            console.log('🔗 Existing wallet linked:', wallet);
            showPrivySuccess(wallet.address);
        });
    }
}

/**
 * Show success screen with wallet address
 */
function showPrivySuccess(walletAddress) {
    const successContainer = document.getElementById('privySuccessContainer');
    const addressEl = document.getElementById('privyWalletAddress');
    
    if (successContainer && addressEl) {
        addressEl.textContent = walletAddress;
        successContainer.style.display = 'block';
        
        // Store wallet info for session
        sessionStorage.setItem('privy_wallet_address', walletAddress);
        sessionStorage.setItem('privy_wallet_created', 'true');
    }
}

/**
 * Continue to claim page after wallet creation
 */
function continueToClaim() {
    const walletAddress = sessionStorage.getItem('privy_wallet_address');
    if (walletAddress) {
        window.location.href = '/claim?wallet=' + walletAddress + '&method=privy';
    } else {
        // Fallback to homepage if no wallet
        window.location.href = '/wallet';
    }
}

/**
 * Get the Privy provider for external use (e.g., for signing)
 */
function getPrivyProvider() {
    return privyProvider;
}

/**
 * Check if user has a Privy wallet in session
 */
function hasPrivyWallet() {
    return sessionStorage.getItem('privy_wallet_created') === 'true';
}
