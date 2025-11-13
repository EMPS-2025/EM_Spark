// // public/custom.js - ChatGPT-Style Enhancements
// // ===============================================

// (function() {
//   'use strict';
  
//   // Wait for DOM to be ready
//   const onReady = () => {
//     console.log('✅ EM Spark UI initialized');
    
//     // 1. Enhanced placeholder text
//     updatePlaceholder();
    
//     // 2. Auto-focus input on load
//     focusInput();
    
//     // 3. Add quick action buttons
//     addQuickActions();
    
//     // 4. Handle keyboard shortcuts
//     setupKeyboardShortcuts();
    
//     // 5. Add welcome animation
//     addWelcomeAnimation();
    
//     // Watch for dynamic content changes
//     observeChanges();
//   };
  
//   // ═══════════════════════════════════════════════════════════
//   // 1. Enhanced Placeholder
//   // ═══════════════════════════════════════════════════════════
  
//   function updatePlaceholder() {
//     const setPlaceholder = () => {
//       const textarea = document.querySelector('textarea');
//       if (textarea && !textarea.dataset.placeholderSet) {
//         textarea.placeholder = "Ask about energy markets... e.g., 'DAM yesterday' or 'GDAM 20-50 slots Oct 2024'";
//         textarea.dataset.placeholderSet = 'true';
//       }
//     };
    
//     setPlaceholder();
//     setInterval(setPlaceholder, 1000);
//   }
  
//   // ═══════════════════════════════════════════════════════════
//   // 2. Auto-focus Input
//   // ═══════════════════════════════════════════════════════════
  
//   function focusInput() {
//     setTimeout(() => {
//       const textarea = document.querySelector('textarea');
//       if (textarea) {
//         textarea.focus();
//       }
//     }, 500);
//   }
  
//   // ═══════════════════════════════════════════════════════════
//   // 3. Quick Action Buttons
//   // ═══════════════════════════════════════════════════════════
  
//   function addQuickActions() {
//     // Check if already added
//     if (document.getElementById('quick-actions')) return;
    
//     // Create container
//     const container = document.createElement('div');
//     container.id = 'quick-actions';
//     container.innerHTML = `
//       <style>
//         #quick-actions {
//           max-width: 48rem;
//           margin: 1rem auto;
//           padding: 0 1rem;
//         }
        
//         .quick-actions-grid {
//           display: grid;
//           grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
//           gap: 0.75rem;
//           margin-top: 1rem;
//         }
        
//         .quick-action-btn {
//           padding: 0.75rem 1rem;
//           background: white;
//           border: 1px solid #e5e7eb;
//           border-radius: 0.75rem;
//           font-size: 0.875rem;
//           cursor: pointer;
//           transition: all 0.2s ease;
//           text-align: left;
//           box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
//         }
        
//         .quick-action-btn:hover {
//           border-color: #2563eb;
//           background: #eff6ff;
//           transform: translateY(-1px);
//           box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
//         }
        
//         .quick-action-btn:active {
//           transform: translateY(0);
//         }
        
//         .quick-action-btn .emoji {
//           font-size: 1.25rem;
//           margin-right: 0.5rem;
//         }
        
//         .quick-action-btn .text {
//           color: #374151;
//           font-weight: 500;
//         }
        
//         #quick-actions-title {
//           font-size: 0.875rem;
//           font-weight: 600;
//           color: #6b7280;
//           text-transform: uppercase;
//           letter-spacing: 0.05em;
//           margin-bottom: 0.5rem;
//         }
//       </style>
      
//       <div id="quick-actions-title">Quick Examples</div>
//       <div class="quick-actions-grid">
//         <button class="quick-action-btn" data-query="DAM yesterday">
//           <span class="emoji">📊</span>
//           <span class="text">DAM Yesterday</span>
//         </button>
//         <button class="quick-action-btn" data-query="GDAM today">
//           <span class="emoji">🟢</span>
//           <span class="text">GDAM Today</span>
//         </button>
//         <button class="quick-action-btn" data-query="Compare Nov 2022, 2023, 2024">
//           <span class="emoji">📈</span>
//           <span class="text">Compare Years</span>
//         </button>
//         <button class="quick-action-btn" data-query="Show detailed list for last week">
//           <span class="emoji">📋</span>
//           <span class="text">Detailed List</span>
//         </button>
//       </div>
//     `;
    
//     // Insert after welcome message or at top of messages
//     const messagesContainer = document.querySelector('[data-testid="messages-container"], .cl__messages, main');
//     if (messagesContainer) {
//       messagesContainer.insertAdjacentElement('afterbegin', container);
      
//       // Add click handlers
//       container.querySelectorAll('.quick-action-btn').forEach(btn => {
//         btn.addEventListener('click', () => {
//           const query = btn.dataset.query;
//           sendMessage(query);
//         });
//       });
//     }
//   }
  
//   // ═══════════════════════════════════════════════════════════
//   // 4. Keyboard Shortcuts
//   // ═══════════════════════════════════════════════════════════
  
//   function setupKeyboardShortcuts() {
//     document.addEventListener('keydown', (e) => {
//       // Cmd/Ctrl + K to focus input
//       if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
//         e.preventDefault();
//         const textarea = document.querySelector('textarea');
//         if (textarea) {
//           textarea.focus();
//           textarea.select();
//         }
//       }
      
//       // Escape to clear input
//       if (e.key === 'Escape') {
//         const textarea = document.querySelector('textarea');
//         if (textarea && document.activeElement === textarea) {
//           textarea.value = '';
//           textarea.blur();
//         }
//       }
//     });
//   }
  
//   // ═══════════════════════════════════════════════════════════
//   // 5. Welcome Animation
//   // ═══════════════════════════════════════════════════════════
  
//   function addWelcomeAnimation() {
//     const style = document.createElement('style');
//     style.textContent = `
//       @keyframes fadeInUp {
//         from {
//           opacity: 0;
//           transform: translateY(20px);
//         }
//         to {
//           opacity: 1;
//           transform: translateY(0);
//         }
//       }
      
//       [data-testid="message"] {
//         animation: fadeInUp 0.4s ease-out;
//       }
      
//       #quick-actions {
//         animation: fadeInUp 0.5s ease-out 0.2s both;
//       }
//     `;
//     document.head.appendChild(style);
//   }
  
//   // ═══════════════════════════════════════════════════════════
//   // Helper: Send Message
//   // ═══════════════════════════════════════════════════════════
  
//   function sendMessage(text) {
//     const textarea = document.querySelector('textarea');
//     const sendButton = document.querySelector('[data-testid="send-button"], button[type="submit"]');
    
//     if (textarea) {
//       // Set value
//       textarea.value = text;
      
//       // Trigger input event
//       textarea.dispatchEvent(new Event('input', { bubbles: true }));
      
//       // Focus
//       textarea.focus();
      
//       // Click send button
//       setTimeout(() => {
//         if (sendButton && !sendButton.disabled) {
//           sendButton.click();
//         }
//       }, 100);
//     }
//   }
  
//   // ═══════════════════════════════════════════════════════════
//   // Observer: Watch for Dynamic Changes
//   // ═══════════════════════════════════════════════════════════
  
//   function observeChanges() {
//     const observer = new MutationObserver(() => {
//       updatePlaceholder();
      
//       // Re-add quick actions if removed
//       if (!document.getElementById('quick-actions')) {
//         setTimeout(addQuickActions, 500);
//       }
//     });
    
//     observer.observe(document.body, {
//       childList: true,
//       subtree: true
//     });
//   }
  
//   // ═══════════════════════════════════════════════════════════
//   // Initialize
//   // ═══════════════════════════════════════════════════════════
  
//   if (document.readyState === 'loading') {
//     document.addEventListener('DOMContentLoaded', onReady);
//   } else {
//     onReady();
//   }
  
// })();

// public/custom.js - Remove Chainlit Branding + Enhanced Features
// ==================================================================

(function() {
  'use strict';
  
  const onReady = () => {
    console.log('✅ EM Spark initialized');
    
    // 1. Remove all Chainlit branding
    removeChainlitBranding();
    
    // 2. Enhanced placeholder
    updatePlaceholder();
    
    // 3. Quick actions
    addQuickActions();
    
    // 4. Watch for changes
    observeChanges();
    
    // 5. Custom header
    addCustomHeader();
  };
  
  // ═══════════════════════════════════════════════════════════
  // 1. REMOVE ALL CHAINLIT BRANDING
  // ═══════════════════════════════════════════════════════════
  
  function removeChainlitBranding() {
    // Remove Chainlit logo
    const removeLogos = () => {
      // Find and remove logo images
      document.querySelectorAll('img[alt*="Chainlit"], img[src*="chainlit"], img[alt*="chainlit"]').forEach(el => {
        el.style.display = 'none';
        el.remove();
      });
      
      // Find and remove logo links
      document.querySelectorAll('a[href*="chainlit"]').forEach(el => {
        el.style.display = 'none';
        el.remove();
      });
      
      // Remove footer
      document.querySelectorAll('footer, [data-testid="footer"]').forEach(el => {
        el.style.display = 'none';
        el.remove();
      });
      
      // Hide sidebar
      document.querySelectorAll('[data-testid="sidebar"], aside, .MuiDrawer-root').forEach(el => {
        el.style.display = 'none';
      });
      
      // Remove "Powered by" text
      document.querySelectorAll('*').forEach(el => {
        if (el.textContent && el.textContent.toLowerCase().includes('powered by chainlit')) {
          el.style.display = 'none';
          el.remove();
        }
      });
    };
    
    removeLogos();
    setInterval(removeLogos, 1000); // Keep checking
  }
  
  // ═══════════════════════════════════════════════════════════
  // 2. CUSTOM HEADER
  // ═══════════════════════════════════════════════════════════
  
  function addCustomHeader() {
    if (document.getElementById('custom-header')) return;
    
    const header = document.createElement('div');
    header.id = 'custom-header';
    header.innerHTML = `
      <style>
        #custom-header {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          height: 60px;
          background: linear-gradient(135deg, #2563eb, #1e40af);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 2rem;
          z-index: 100;
        }
        
        #custom-header .logo {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }
        
        #custom-header .logo-icon {
          width: 32px;
          height: 32px;
          background: white;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          color: #2563eb;
          font-size: 1.25rem;
        }
        
        #custom-header .logo-text {
          color: white;
          font-size: 1.25rem;
          font-weight: 700;
          letter-spacing: -0.02em;
        }
        
        #custom-header .tagline {
          color: rgba(255, 255, 255, 0.9);
          font-size: 0.875rem;
          font-weight: 500;
        }
        
        /* Adjust main content to account for header */
        .cl__messages,
        [data-testid="messages-container"],
        main {
          margin-top: 80px !important;
        }
        
        @media (max-width: 768px) {
          #custom-header {
            padding: 0 1rem;
          }
          
          #custom-header .tagline {
            display: none;
          }
        }
      </style>
      
      <div class="logo">
        <div class="logo-icon">⚡</div>
        <div class="logo-text">EM Spark</div>
      </div>
      <div class="tagline">Energy Market Intelligence</div>
    `;
    
    document.body.insertBefore(header, document.body.firstChild);
  }
  
  // ═══════════════════════════════════════════════════════════
  // 3. ENHANCED PLACEHOLDER
  // ═══════════════════════════════════════════════════════════
  
  function updatePlaceholder() {
    const setPlaceholder = () => {
      const textarea = document.querySelector('textarea');
      if (textarea && !textarea.dataset.customPlaceholder) {
        textarea.placeholder = "Ask about energy markets... e.g., 'DAM yesterday' or 'Compare Nov 2022 vs 2023'";
        textarea.dataset.customPlaceholder = 'true';
      }
    };
    
    setPlaceholder();
    setInterval(setPlaceholder, 1000);
  }
  
  // ═══════════════════════════════════════════════════════════
  // 4. QUICK ACTION BUTTONS
  // ═══════════════════════════════════════════════════════════
  
  function addQuickActions() {
    if (document.getElementById('quick-actions')) return;
    
    const container = document.createElement('div');
    container.id = 'quick-actions';
    container.innerHTML = `
      <style>
        #quick-actions {
          max-width: 1200px;
          margin: 0 auto 2rem;
          padding: 0 1rem;
        }
        
        .quick-actions-title {
          font-size: 0.875rem;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 1rem;
        }
        
        .quick-actions-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 1rem;
        }
        
        .quick-action-card {
          background: white;
          border: 2px solid #e5e7eb;
          border-radius: 1rem;
          padding: 1.25rem;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
        }
        
        .quick-action-card:hover {
          border-color: #2563eb;
          transform: translateY(-2px);
          box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
        }
        
        .quick-action-card .icon {
          font-size: 2rem;
          margin-bottom: 0.5rem;
        }
        
        .quick-action-card .title {
          font-weight: 600;
          color: #111827;
          margin-bottom: 0.25rem;
        }
        
        .quick-action-card .description {
          font-size: 0.875rem;
          color: #6b7280;
        }
      </style>
      
      <div class="quick-actions-title">Quick Examples</div>
      <div class="quick-actions-grid">
        <div class="quick-action-card" data-query="DAM today">
          <div class="icon">📊</div>
          <div class="title">Today's DAM</div>
          <div class="description">Current market prices</div>
        </div>
        
        <div class="quick-action-card" data-query="GDAM today">
          <div class="icon">🟢</div>
          <div class="title">GDAM Today</div>
          <div class="description">Green energy market</div>
        </div>
        
        <div class="quick-action-card" data-query="Compare DAM and GDAM yesterday">
          <div class="icon">📈</div>
          <div class="title">DAM vs GDAM</div>
          <div class="description">Side-by-side comparison</div>
        </div>
        
        <div class="quick-action-card" data-query="Compare Nov 2023 vs Nov 2024">
          <div class="icon">📉</div>
          <div class="title">Year Over Year</div>
          <div class="description">Historical comparison</div>
        </div>
      </div>
    `;
    
    const messagesContainer = document.querySelector('[data-testid="messages-container"], .cl__messages, main');
    if (messagesContainer) {
      messagesContainer.insertAdjacentElement('afterbegin', container);
      
      container.querySelectorAll('.quick-action-card').forEach(card => {
        card.addEventListener('click', () => {
          const query = card.dataset.query;
          sendMessage(query);
        });
      });
    }
  }
  
  // ═══════════════════════════════════════════════════════════
  // HELPER: SEND MESSAGE
  // ═══════════════════════════════════════════════════════════
  
  function sendMessage(text) {
    const textarea = document.querySelector('textarea');
    const sendButton = document.querySelector('[data-testid="send-button"]');
    
    if (textarea) {
      textarea.value = text;
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
      textarea.focus();
      
      setTimeout(() => {
        if (sendButton && !sendButton.disabled) {
          sendButton.click();
        }
      }, 100);
    }
  }
  
  // ═══════════════════════════════════════════════════════════
  // OBSERVER: WATCH FOR CHANGES
  // ═══════════════════════════════════════════════════════════
  
  function observeChanges() {
    const observer = new MutationObserver(() => {
      removeChainlitBranding();
      updatePlaceholder();
      
      if (!document.getElementById('quick-actions')) {
        setTimeout(addQuickActions, 500);
      }
      
      if (!document.getElementById('custom-header')) {
        addCustomHeader();
      }
    });
    
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }
  
  // ═══════════════════════════════════════════════════════════
  // INITIALIZE
  // ═══════════════════════════════════════════════════════════
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onReady);
  } else {
    onReady();
  }
  
})();
