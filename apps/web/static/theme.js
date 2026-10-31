// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
'use strict';
(() => {
 const root=document.documentElement;
 let theme='dark';try{const saved=localStorage.getItem('dracula-theme');if(saved==='light'||saved==='dark')theme=saved;}catch{}
 root.dataset.theme=theme;
 const paint=()=>{for(const button of document.querySelectorAll('[data-theme-toggle]')){button.textContent=theme==='dark'?'☀ Light mode':'☾ Dark mode';button.setAttribute('aria-label',theme==='dark'?'Switch to light mode':'Switch to dark mode');}};
 document.addEventListener('DOMContentLoaded',()=>{paint();for(const button of document.querySelectorAll('[data-theme-toggle]'))button.addEventListener('click',()=>{theme=theme==='dark'?'light':'dark';root.dataset.theme=theme;try{localStorage.setItem('dracula-theme',theme);}catch{}paint();});});
})();
