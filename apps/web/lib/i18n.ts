/* Three languages, one document.
 *
 * Arabic is not a translation layer bolted on: `dir` flips the whole document,
 * the nav mirrors, and numerals stay Western because that is how prices and
 * times are set in UAE retail. Hindi shares the Latin direction and needs its
 * own face for Devanagari.
 *
 * Only interface chrome is translated here. Data — a zone name, an event title,
 * a compliance clause — carries its own language from the source, because
 * machine-translating a regulatory clause into a language the reader will act
 * on is exactly the kind of confident wrongness this project argues against.
 */

export const LOCALES = ["en", "hi", "ar"] as const;
export type Locale = (typeof LOCALES)[number];

export const DIR: Record<Locale, "ltr" | "rtl"> = { en: "ltr", hi: "ltr", ar: "rtl" };
export const LOCALE_NAME: Record<Locale, string> = { en: "English", hi: "हिन्दी", ar: "العربية" };

type Dict = Record<string, string>;

const en: Dict = {
  "app.name": "MAWSIM",
  "app.tagline": "Demand-aware promo planning",
  "app.course": "AI 208 · SP Jain MAIB Term 4",
  "brand.fictional": "SIDRA is a fictional brand, built for this demonstration.",
  "brand.simulated": "Footfall is simulated.",

  "group.plan": "Plan",
  "group.make": "Make",
  "group.prove": "Prove",
  "group.system": "System",

  "tab.season": "Season",
  "tab.forecast": "Forecast",
  "tab.plan": "Plan",
  "tab.segments": "Segments",
  "tab.creatives": "Creatives",
  "tab.brand": "Brand",
  "tab.compliance": "Compliance",
  "tab.panel": "Panel",
  "tab.measure": "Measure",
  "tab.experiments": "Experiments",
  "tab.report": "Report",
  "tab.ask": "Ask",
  "tab.crew": "Crew",
  "tab.data": "Data",
  "tab.security": "Security",

  "theme.label": "Colour register",
  "theme.auto": "Auto",
  "theme.light": "Day",
  "theme.dark": "Night",
  "lang.label": "Language",

  "scaffold.title": "Not built yet",
  "scaffold.phase": "Arrives in Phase",
  "scaffold.why":
    "This page is deliberately empty rather than filled with placeholder numbers. Nothing in this application shows a figure it cannot trace to docs/results/.",

  "a11y.skip": "Skip to content",
  "a11y.nav": "Sections",
};

const hi: Dict = {
  ...en,
  "app.tagline": "मांग-आधारित प्रोमो योजना",
  "brand.fictional": "SIDRA एक काल्पनिक ब्रांड है, इस प्रदर्शन के लिए बनाया गया।",
  "brand.simulated": "फुटफॉल सिम्युलेटेड है।",
  "group.plan": "योजना",
  "group.make": "निर्माण",
  "group.prove": "प्रमाण",
  "group.system": "सिस्टम",
  "tab.season": "मौसम",
  "tab.forecast": "पूर्वानुमान",
  "tab.plan": "योजना",
  "tab.segments": "खंड",
  "tab.creatives": "क्रिएटिव",
  "tab.brand": "ब्रांड",
  "tab.compliance": "अनुपालन",
  "tab.panel": "पैनल",
  "tab.measure": "मापन",
  "tab.experiments": "प्रयोग",
  "tab.report": "रिपोर्ट",
  "tab.ask": "पूछें",
  "tab.crew": "क्रू",
  "tab.data": "डेटा",
  "tab.security": "सुरक्षा",
  "theme.label": "रंग रजिस्टर",
  "theme.auto": "स्वतः",
  "theme.light": "दिन",
  "theme.dark": "रात",
  "lang.label": "भाषा",
  "scaffold.title": "अभी नहीं बना",
  "scaffold.phase": "चरण में आएगा",
  "a11y.skip": "मुख्य सामग्री पर जाएँ",
  "a11y.nav": "अनुभाग",
};

const ar: Dict = {
  ...en,
  "app.tagline": "تخطيط العروض حسب الطلب",
  "brand.fictional": "‏SIDRA علامة تجارية خيالية أُنشئت لهذا العرض التوضيحي.",
  "brand.simulated": "بيانات الإقبال محاكاة.",
  "group.plan": "التخطيط",
  "group.make": "الإنتاج",
  "group.prove": "الإثبات",
  "group.system": "النظام",
  "tab.season": "الموسم",
  "tab.forecast": "التوقعات",
  "tab.plan": "الخطة",
  "tab.segments": "الشرائح",
  "tab.creatives": "التصاميم",
  "tab.brand": "العلامة",
  "tab.compliance": "الامتثال",
  "tab.panel": "اللجنة",
  "tab.measure": "القياس",
  "tab.experiments": "التجارب",
  "tab.report": "التقرير",
  "tab.ask": "اسأل",
  "tab.crew": "الفريق",
  "tab.data": "البيانات",
  "tab.security": "الأمان",
  "theme.label": "سجل الألوان",
  "theme.auto": "تلقائي",
  "theme.light": "نهار",
  "theme.dark": "ليل",
  "lang.label": "اللغة",
  "scaffold.title": "لم يُبنَ بعد",
  "scaffold.phase": "سيصل في المرحلة",
  "a11y.skip": "تخطّي إلى المحتوى",
  "a11y.nav": "الأقسام",
};

const DICTS: Record<Locale, Dict> = { en, hi, ar };

export function t(locale: Locale, key: string): string {
  return DICTS[locale][key] ?? DICTS.en[key] ?? key;
}
