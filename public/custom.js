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
    
//     // 6. Watch for dynamic content changes
//     observeChanges();
//   };

//   // ═══════════════════════════════════════════════════════════
//   // 1. Enhanced Placeholder
//   // ═══════════════════════════════════════════════════════════
//   function updatePlaceholder() {
//     const setPlaceholder = () => {
//       const textarea = document.querySelector('textarea');
//       if (textarea && !textarea.dataset.placeholderSet) {
//         textarea.placeholder = "Ask about energy markets... e.g., 'DAM yesterday' or 'GDAM 20-50 slots'";
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
//     if (document.getElementById('quick-actions')) return;

//     const examples = [
//       { emoji: '📊', text: 'DAM rate today', query: 'DAM rate for today' },
//       { emoji: '🟢', text: 'GDAM yesterday', query: 'GDAM rate for yesterday' },
//       { emoji: '🔵', text: 'RTM last hour', query: 'RTM rate for last hour' },
//       { emoji: '📈', text: 'Compare markets', query: 'Compare DAM and GDAM for today' },
//     ];

//     const container = document.createElement('div');
//     container.id = 'quick-actions';
//     container.style.cssText = `
//       display: flex;
//       flex-wrap: wrap;
//       gap: 0.5rem;
//       margin-top: 1rem;
//       padding: 0 1rem;
//     `;

//     examples.forEach(ex => {
//       const btn = document.createElement('button');
//       btn.innerHTML = `${ex.emoji} ${ex.text}`;
//       btn.style.cssText = `
//         padding: 0.5rem 1rem;
//         border-radius: 0.5rem;
//         border: 1px solid #e5e7eb;
//         background: white;
//         color: #111827;
//         font-size: 0.875rem;
//         cursor: pointer;
//         transition: all 0.2s ease;
//       `;
      
//       btn.onmouseover = () => {
//         btn.style.background = '#f3f4f6';
//         btn.style.borderColor = '#2563eb';
//       };
      
//       btn.onmouseout = () => {
//         btn.style.background = 'white';
//         btn.style.borderColor = '#e5e7eb';
//       };
      
//       btn.onclick = () => {
//         const textarea = document.querySelector('textarea');
//         if (textarea) {
//           textarea.value = ex.query;
//           textarea.focus();
//           textarea.dispatchEvent(new Event('input', { bubbles: true }));
//         }
//       };
      
//       container.appendChild(btn);
//     });

//     setTimeout(() => {
//       const inputArea = document.querySelector('.cl__composer, [data-testid="input-box"]');
//       if (inputArea) {
//         inputArea.insertAdjacentElement('beforebegin', container);
//       }
//     }, 1000);
//   }

//   // ═══════════════════════════════════════════════════════════
//   // 4. Keyboard Shortcuts
//   // ═══════════════════════════════════════════════════════════
//   function setupKeyboardShortcuts() {
//     document.addEventListener('keydown', (e) => {
//       // Cmd/Ctrl + K to focus search
//       if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
//         e.preventDefault();
//         const textarea = document.querySelector('textarea');
//         if (textarea) textarea.focus();
//       }
      
//       // Cmd/Ctrl + Enter to submit
//       if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
//         e.preventDefault();
//         const button = document.querySelector('[data-testid="send-button"]');
//         if (button) button.click();
//       }
//     });
//   }

//   // ═══════════════════════════════════════════════════════════
//   // 5. Welcome Animation
//   // ═══════════════════════════════════════════════════════════
//   function addWelcomeAnimation() {
//     const style = document.createElement('style');
//     style.textContent = `
//       @keyframes slideDown {
//         from {
//           opacity: 0;
//           transform: translateY(-20px);
//         }
//         to {
//           opacity: 1;
//           transform: translateY(0);
//         }
//       }
      
//       .cl__message {
//         animation: slideDown 0.3s ease-out;
//       }
//     `;
//     document.head.appendChild(style);
//   }

//   // ═══════════════════════════════════════════════════════════
//   // 6. Watch for Dynamic Content Changes
//   // ═══════════════════════════════════════════════════════════
//   function observeChanges() {
//     const observer = new MutationObserver(() => {
//       // Re-apply placeholder if DOM changed
//       const textarea = document.querySelector('textarea');
//       if (textarea && !textarea.dataset.placeholderSet) {
//         updatePlaceholder();
//       }
//     });

//     const config = { 
//       childList: true, 
//       subtree: true,
//       attributes: false,
//       characterData: false 
//     };
    
//     const rootElement = document.documentElement;
//     observer.observe(rootElement, config);
//   }

//   // Initialize when DOM is ready
//   if (document.readyState === 'loading') {
//     document.addEventListener('DOMContentLoaded', onReady);
//   } else {
//     onReady();
//   }

//   // Also initialize after a short delay to catch late-loading content
//   setTimeout(onReady, 1000);

// })();
