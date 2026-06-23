/**
 * Magic.link Embedded Wallet Integration
 * Handles wallet creation via email, Google, phone, social logins
 * Supports Celo network
 */

let magic = null;
let magicUser = null;
let magicWalletAddress = null;

/**
 * Initialize and show the Magic wallet creation form
 */
function showPrivyForm() {
    document.getElementById('walletOptions').style.display = 'none';
    document.getElementById('privyFormContainer').classList.add('visible');
    document.getElementById('privySuccessContainer').style.display = 'none';
    document.getElementById('privy-embed-container').style.display = 'block';
    initMagic();
}

/**
 * Initialize Magic SDK
 */
async function initMagic() {
    const container = document.getElementById('privy-embed-container');
    if (!container) {
        console.error('Magic container not found');
        return;
    }

    // Get API Key from template variable
    const MAGIC_API_KEY = typeof PRIVY_APP_ID_VAR !== 'undefined' ? PRIVY_APP_ID_VAR : '';

    if (!MAGIC_API_KEY) {
        container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #6b7280;">
                <p style="margin-bottom: 1rem;">⚠️ Magic.link API Key not configured</p>
                <p style="font-size: 0.85rem;">Please set the MAGIC_API_KEY environment variable to enable wallet creation.</p>
                <p style="font-size: 0.75rem; margin-top: 1rem;">Get your API Key at <a href="https://magic.link" target="_blank" style="color: #7c3aed;">magic.link</a></p>
            </div>
        `;
        return;
    }

    try {
        // Check if Magic is loaded
        if (typeof Magic === 'undefined') {
            container.innerHTML = `
                <div style="padding: 2rem; text-align: center; color: #6b7280;">
                    <div class="spinner" style="margin: 0 auto 1rem;"></div>
                    <p>Loading Magic SDK...</p>
                </div>
            `;
            
            // Wait for Magic to load, then retry
            setTimeout(() => initMagic(), 500);
            return;
        }

        // Initialize Magic with Celo support
        magic = new Magic(MAGIC_API_KEY, {
            network: {
                chainId: 42220, // Celo Mainnet
                rpcUrl: 'https://forno.celo.org',
            },
        });

        // Check if user is already logged in
        const isLoggedIn = await magic.user.isLoggedIn();
        
        if (isLoggedIn) {
            // Get existing wallet address
            const info = await magic.user.getInfo();
            if (info && info.publicAddress) {
                magicWalletAddress = info.publicAddress;
                showMagicSuccess(info.publicAddress);
                return;
            }
        }

        // Show login form
        showMagicLoginForm();

    } catch (error) {
        console.error('❌ Magic init error:', error);
        container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #ef4444;">
                <p>Failed to initialize wallet creator.</p>
                <p style="font-size: 0.85rem; color: #6b7280; margin-top: 0.5rem;">${error.message || 'Please try again.'}</p>
            </div>
        `;
    }
}

/**
 * Show Magic login/email form
 */
function showMagicLoginForm() {
    const container = document.getElementById('privy-embed-container');
    container.innerHTML = `
        <div style="padding: 1rem;">
            <div style="text-align: center; margin-bottom: 1.5rem;">
                <h3 style="color: #1f2937; margin-bottom: 0.5rem;">Create Your Web3 Wallet</h3>
                <p style="color: #6b7280; font-size: 0.85rem;">Enter your email to get started - no setup needed!</p>
            </div>
            
            <form id="magicEmailForm" style="display: flex; flex-direction: column; gap: 1rem;">
                <div>
                    <label style="display: block; font-size: 0.85rem; color: #374151; margin-bottom: 0.5rem;">Email Address</label>
                    <input 
                        type="email" 
                        id="magicEmailInput" 
                        placeholder="you@example.com"
                        required
                        style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 8px; font-size: 1rem;"
                    >
                </div>
                <button 
                    type="submit" 
                    id="magicLoginBtn"
                    style="background: linear-gradient(135deg, #7c3aed, #6d28d9); color: white; border: none; padding: 0.875rem; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 1rem;"
                >
                    Get Wallet
                </button>
            </form>
            
            <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #e5e7eb;">
                <p style="font-size: 0.75rem; color: #9ca3af; text-align: center;">
                    By continuing, you agree to our Terms of Service
                </p>
            </div>
        </div>
    `;

    // Handle form submission
    document.getElementById('magicEmailForm').addEventListener('submit', handleMagicLogin);
}

/**
 * Handle Magic login with email OTP
 */
async function handleMagicLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('magicEmailInput').value.trim();
    const btn = document.getElementById('magicLoginBtn');
    
    if (!email) {
        alert('Please enter your email address');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Sending code...';

    try {
        // Request magic link (DID token for email)
        await magic.auth.loginWithEmailOTP({ email });
        
        btn.textContent = 'Check your email!';
        
        // After OTP verification, get wallet
        // The user will click the magic link to verify
        // Then we can get their wallet address
        
        // Show verification message
        const container = document.getElementById('privy-embed-container');
        container.innerHTML = `
            <div style="padding: 2rem; text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📧</div>
                <h3 style="color: #1f2937; margin-bottom: 0.5rem;">Check Your Email!</h3>
                <p style="color: #6b7280; font-size: 0.85rem; margin-bottom: 1rem;">
                    We sent a verification link to<br>
                    <strong>${email}</strong>
                </p>
                <p style="color: #9ca3af; font-size: 0.75rem;">
                    Click the link in your email to continue
                </p>
                <button 
                    onclick="checkMagicLogin()"
                    style="background: #f3f4f6; color: #374151; border: none; padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.85rem; cursor: pointer; margin-top: 1rem;"
                >
                    I verified, continue
                </button>
            </div>
        `;

    } catch (error) {
        console.error('Magic login error:', error);
        btn.disabled = false;
        btn.textContent = 'Get Wallet';
        alert('Login failed: ' + (error.message || 'Please try again'));
    }
}

/**
 * Check if user completed Magic login
 */
async function checkMagicLogin() {
    try {
        const isLoggedIn = await magic.user.isLoggedIn();
        
        if (isLoggedIn) {
            const info = await magic.user.getInfo();
            if (info && info.publicAddress) {
                showMagicSuccess(info.publicAddress);
                return;
            }
        }
        
        // Not verified yet
        alert('Please verify your email first by clicking the link we sent.');
        
    } catch (error) {
        console.error('Check login error:', error);
        alert('Something went wrong. Please try again.');
    }
}

/**
 * Show success screen with wallet address
 */
function showMagicSuccess(walletAddress) {
    const container = document.getElementById('privy-embed-container');
    const successContainer = document.getElementById('privySuccessContainer');
    const addressEl = document.getElementById('privyWalletAddress');
    
    // Hide the container and show success
    if (container) container.style.display = 'none';
    
    if (successContainer && addressEl) {
        addressEl.textContent = walletAddress;
        successContainer.style.display = 'block';
        
        // Store wallet info for session
        sessionStorage.setItem('magic_wallet_address', walletAddress);
        sessionStorage.setItem('magic_wallet_created', 'true');
    }
}

/**
 * Continue to claim page after wallet creation
 */
function continueToClaim() {
    const walletAddress = sessionStorage.getItem('magic_wallet_address');
    if (walletAddress) {
        window.location.href = '/claim?wallet=' + walletAddress + '&method=magic';
    } else {
        window.location.href = '/wallet';
    }
}

/**
 * Get Magic provider for web3 operations
 */
function getMagicProvider() {
    if (magic) {
        return magic.rpcProvider;
    }
    return null;
}

/**
 * Check if user has a Magic wallet in session
 */
function hasMagicWallet() {
    return sessionStorage.getItem('magic_wallet_created') === 'true';
}

/**
 * Logout user
 */
async function magicLogout() {
    if (magic) {
        await magic.user.logout();
        sessionStorage.removeItem('magic_wallet_address');
        sessionStorage.removeItem('magic_wallet_created');
    }
}
