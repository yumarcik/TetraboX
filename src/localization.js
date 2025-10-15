// Localization system for TetraboX UI
const localization = {
  tr: {
    // Header and Navigation
    "ORDER_LIST": "SİPARİŞ LİSTESİ",
    "SELECTED_ORDER": "SEÇİLEN SİPARİŞ",
    "PACK_ORDER": "Siparişi Paketle",
    
    // Order Details
    "ITEMS": "ÜRÜNLER",
    "ITEMS_COUNT": "ürün",
    "DATE": "TARİH",
    "TOTAL": "TOPLAM",
    "PRODUCTS": "Ürünler",
    
    // Packing Results
    "PACKING_COMPLETE": "Paketleme Tamamlandı",
    "UTILIZATION": "kullanım",
    
    // Container Details
    "CONTAINER": "KONTEYNER",
    "CONTAINER_ITEMS": "ÜRÜNLER",
    "CONTAINER_UTILIZATION": "KULLANIM",
    "CONTAINER_PRICE": "FİYAT",
    "CONTAINER_VOLUME": "HACİM",
    "CONTAINER_DIMENSIONS": "BOYUTLAR",
    
    // Solution Description
    "PERFECT_SOLUTION": "Mükemmel Tek Konteyner Çözümü",
    "SOLUTION_DESCRIPTION": "Tüm <strong>{items} ürün</strong> <strong>{container}</strong> konteynerinde <strong>{company}</strong> şirketinden mükemmel şekilde sığıyor. Bu <strong>{utilization}% kullanım</strong> ile en uygun maliyetli çözümdür.",
    
    // 3D/2D Views
    "3D_CONTAINER_VIEW": "3D KONTEYNER GÖRÜNÜMÜ",
    "3D_VIEW": "3D Görünüm",
    "2D_VIEWS": "2D Görünümler",
    "RAW_DATA": "Ham Veri",
    
    // 2D View Labels
    "BIRDS_EYE_VIEW": "Kuş Bakışı Görünüm",
    "BIRDS_EYE_SUBTITLE": "Yukarıdan bakış",
    "FRONT_VIEW": "Ön Görünüm",
    "FRONT_VIEW_SUBTITLE": "Konteyner yüzüne bakış",
    "SIDE_VIEW": "Yan Görünüm",
    "SIDE_VIEW_SUBTITLE": "Yandan bakış",
    
    // Controls
    "CONTROLS": "Kontroller",
    "3D_INTERACTION": "3D Etkileşim",
    "RESET_VIEW": "Görünümü Sıfırla",
    "AUTO_ROTATE": "Otomatik Döndür",
    "SHORTCUTS": "Kısayollar",
    "ROTATE_VIEW": "Görünümü döndür",
    "ZOOM_IN_OUT": "Yakınlaştır/Uzaklaştır",
    "ITEM_DETAILS": "Ürün detayları",
    
    // Search and UI
    "SEARCH_PLACEHOLDER": "ID veya müşteri adına göre ara...",
    "QUICK_START_GUIDE": "Hızlı Başlangıç Kılavuzu",
    "QUICK_START_DESCRIPTION": "Siparişler otomatik yüklenir. Sipariş seçin, paketleme butonuna basın ve 3D sonuçları görün!",
    
    // Statistics
    "TOTAL_ORDERS": "Toplam Sipariş",
    "TOTAL_ITEMS": "Toplam Ürün",
    "TOTAL_VALUE": "Toplam Değer",
    
    // Language
    "LANGUAGE": "Dil"
  },
  
  en: {
    // Header and Navigation
    "ORDER_LIST": "ORDER LIST",
    "SELECTED_ORDER": "SELECTED ORDER",
    "PACK_ORDER": "Pack Order",
    
    // Order Details
    "ITEMS": "ITEMS",
    "ITEMS_COUNT": "items",
    "DATE": "DATE",
    "TOTAL": "TOTAL",
    "PRODUCTS": "Products",
    
    // Packing Results
    "PACKING_COMPLETE": "Packing Complete",
    "UTILIZATION": "utilization",
    
    // Container Details
    "CONTAINER": "CONTAINER",
    "CONTAINER_ITEMS": "ITEMS",
    "CONTAINER_UTILIZATION": "UTILIZATION",
    "CONTAINER_PRICE": "PRICE",
    "CONTAINER_VOLUME": "VOLUME",
    "CONTAINER_DIMENSIONS": "DIMENSIONS",
    
    // Solution Description
    "PERFECT_SOLUTION": "Perfect Single-Container Solution",
    "SOLUTION_DESCRIPTION": "All <strong>{items} items</strong> fit perfectly in a single <strong>{container}</strong> container from <strong>{company}</strong>. This is the most cost-effective solution with <strong>{utilization}% utilization</strong>.",
    
    // 3D/2D Views
    "3D_CONTAINER_VIEW": "3D CONTAINER VIEW",
    "3D_VIEW": "3D View",
    "2D_VIEWS": "2D Views",
    "RAW_DATA": "Raw Data",
    
    // 2D View Labels
    "BIRDS_EYE_VIEW": "Bird's Eye View",
    "BIRDS_EYE_SUBTITLE": "Looking down from above",
    "FRONT_VIEW": "Front View",
    "FRONT_VIEW_SUBTITLE": "Looking at the container face",
    "SIDE_VIEW": "Side View",
    "SIDE_VIEW_SUBTITLE": "Looking from the side",
    
    // Controls
    "CONTROLS": "Controls",
    "3D_INTERACTION": "3D Interaction",
    "RESET_VIEW": "Reset View",
    "AUTO_ROTATE": "Auto Rotate",
    "SHORTCUTS": "Shortcuts",
    "ROTATE_VIEW": "Rotate view",
    "ZOOM_IN_OUT": "Zoom in/out",
    "ITEM_DETAILS": "Item details",
    
    // Search and UI
    "SEARCH_PLACEHOLDER": "Search by ID or customer...",
    "QUICK_START_GUIDE": "Quick Start Guide",
    "QUICK_START_DESCRIPTION": "Orders load automatically. Select an order, click pack, and see 3D results!",
    
    // Statistics
    "TOTAL_ORDERS": "Total Orders",
    "TOTAL_ITEMS": "Total Items",
    "TOTAL_VALUE": "Total Value",
    
    // Language
    "LANGUAGE": "Language"
  }
};

// Current language (default to Turkish)
let currentLanguage = 'tr';

// Make currentLanguage globally accessible
window.currentLanguage = currentLanguage;

// Get localized text
function t(key, params = {}) {
  let text = localization[currentLanguage][key] || localization.en[key] || key;
  
  // Replace parameters in text
  Object.keys(params).forEach(param => {
    text = text.replace(`{${param}}`, params[param]);
  });
  
  return text;
}

// Switch language
function switchLanguage(lang) {
  currentLanguage = lang;
  window.currentLanguage = lang; // Update global reference
  updateAllTexts();
  
  // Save language preference
  localStorage.setItem('tetrabox-language', lang);
}

// Update all texts on the page
function updateAllTexts() {
  console.log('updateAllTexts called, currentLanguage:', currentLanguage);
  
  // Update elements with data-tr and data-en attributes
  const elements = document.querySelectorAll('[data-tr], [data-en]');
  console.log('Found', elements.length, 'elements with data-tr or data-en attributes');
  
  elements.forEach(element => {
    const trText = element.getAttribute('data-tr');
    const enText = element.getAttribute('data-en');
    
    if (trText && enText) {
      // Check if text contains HTML tags
      if (trText.includes('<') || enText.includes('<')) {
        element.innerHTML = currentLanguage === 'tr' ? trText : enText;
      } else {
        element.textContent = currentLanguage === 'tr' ? trText : enText;
      }
    }
  });
  
  // Update placeholder texts
  document.querySelectorAll('[data-tr-placeholder], [data-en-placeholder]').forEach(element => {
    const trPlaceholder = element.getAttribute('data-tr-placeholder');
    const enPlaceholder = element.getAttribute('data-en-placeholder');
    
    if (trPlaceholder && enPlaceholder) {
      element.placeholder = currentLanguage === 'tr' ? trPlaceholder : enPlaceholder;
    }
  });
  
  // Update dynamic content (like order lists, results, etc.)
  if (typeof renderOrderList === 'function' && typeof window.allOrders !== 'undefined' && window.allOrders.length > 0) {
    console.log('Re-rendering order list with', window.allOrders.length, 'orders, language:', currentLanguage);
    renderOrderList(window.allOrders);
  }
  if (typeof updateSelectedOrderInfo === 'function') {
    updateSelectedOrderInfo();
  }
  
  // Re-render packing results if they exist
  if (typeof window.packingResult !== 'undefined' && window.packingResult) {
    console.log('Re-rendering packing results with language:', currentLanguage);
    if (typeof showCompactResult === 'function') {
      showCompactResult(window.packingResult);
    }
    if (typeof renderSummary === 'function') {
      renderSummary(window.packingResult);
    }
  }
}

// Initialize language from localStorage
function initializeLanguage() {
  const savedLang = localStorage.getItem('tetrabox-language');
  if (savedLang && (savedLang === 'tr' || savedLang === 'en')) {
    currentLanguage = savedLang;
    window.currentLanguage = savedLang; // Update global reference
  }
  updateAllTexts();
}

// Export for use in other scripts
window.localization = {
  t,
  switchLanguage,
  updateAllTexts,
  initializeLanguage,
  currentLanguage: () => currentLanguage,
  getCurrentLanguage: () => currentLanguage
};
