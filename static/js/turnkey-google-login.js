/**
 * turnkey-google-login.js
 *
 * Handles the "Login with Google" flow on the homepage:
 *   1. Loads the Google Identity Services (GIS) library
 *   2. Renders the Google Sign-In button / triggers One Tap
 *   3. Sends the Google id_token to /api/turnkey/google-login
 *   4. On success creates the Flask session and redirects to /wallet
 */
(function () {
  'use strict';

  // ── Globals injected by the template ──────────────────────────────────
  // window.__GOOGLE_CLIENT_ID  – set by the homepage template

  var _gsiLoaded = false;
  var _gsiLoading = null;

  // ── Load the Google Identity Services SDK ─────────────────────────────
  function loadGsi() {
    if (_gsiLoaded && window.google && window.google.accounts) {
      return Promise.resolve();
    }
    if (_gsiLoading) return _gsiLoading;

    _gsiLoading = new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = 'https://accounts.google.com/gsi/client';
      s.async = true;
      s.defer = true;
      s.onload = function () {
        _gsiLoaded = true;
        resolve();
      };
      s.onerror = function () {
        reject(new Error('Failed to load Google Identity Services SDK'));
      };
      document.head.appendChild(s);
    });
    return _gsiLoading;
  }

  // ── Status helper (reuses the existing showWalletStatus if available) ─
  function showStatus(msg, type) {
    var el = document.getElementById('turnkeyGoogleStatus');
    if (!el) return;
    el.className = 'status-message ' + (type || 'info');
    el.textContent = msg;
  }

  // ── Send the id_token to our backend ──────────────────────────────────
  function sendTokenToBackend(idToken, referralCode) {
    showStatus('⏳ Creating your wallet…', 'info');

    return fetch('/api/turnkey/google-login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id_token: idToken,
        referral_code: referralCode || ''
      })
    })
      .then(function (resp) {
        return resp.json().then(function (data) {
          return { ok: resp.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data.success) {
          throw new Error(result.data.error || 'Login failed');
        }
        var warning = result.data.referral_warning;
        var okMsg = warning
          ? '✅ Wallet ready! ⚠️ ' + warning + ' Redirecting…'
          : '✅ Wallet ready! Redirecting…';
        showStatus(okMsg, warning ? 'warning' : 'success');
        setTimeout(function () {
          window.location.href = '/wallet';
        }, warning ? 2400 : 900);
      })
      .catch(function (err) {
        showStatus('❌ ' + (err.message || 'Google login failed'), 'error');
      });
  }

  // ── Google callback (called by GIS after user picks an account) ───────
  function handleGoogleCredentialResponse(response) {
    if (!response || !response.credential) {
      showStatus('❌ Google sign-in was cancelled', 'warning');
      return;
    }
    // Grab any pending referral code from the modal
    var refInput = document.getElementById('googleReferralCode');
    var referralCode = refInput ? refInput.value.trim() : '';
    sendTokenToBackend(response.credential, referralCode);
  }

  // ── Initialise the Google button inside #googleSignInBtnWrap ──────────
  function initGoogleButton() {
    var clientId = window.__GOOGLE_CLIENT_ID;
    if (!clientId) {
      console.warn('[turnkey-google] No GOOGLE_CLIENT_ID configured');
      return;
    }

    loadGsi().then(function () {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleCredentialResponse,
        auto_select: false,
        cancel_on_tap_outside: true,
      });

      var btnWrap = document.getElementById('googleSignInBtnWrap');
      if (btnWrap) {
        window.google.accounts.id.renderButton(btnWrap, {
          type: 'standard',
          theme: 'filled_blue',
          size: 'large',
          text: 'signin_with',
          shape: 'pill',
          width: 300,
        });
      }
    }).catch(function (err) {
      console.error('[turnkey-google] GIS load error:', err);
      showStatus('❌ Could not load Google Sign-In', 'error');
    });
  }

  // ── Public API ────────────────────────────────────────────────────────
  window.TurnkeyGoogleLogin = {
    init: initGoogleButton,
  };
})();
