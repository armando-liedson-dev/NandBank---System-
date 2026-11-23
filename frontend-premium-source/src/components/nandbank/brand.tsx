import { Link } from "@tanstack/react-router";
import lionLogo from "@/assets/nandbank-lion-logo.png.asset.json";

export function BrandMark({ compact = false, monochrome = false }: { compact?: boolean; monochrome?: boolean }) {
  const local = import.meta.env["VITE_LOCAL_ASSETS"] === "true";
  const url = monochrome
    ? (local ? "/static/images/nandbank-lion-black.png" : "/images/nandbank-lion-black.png")
    : (local ? "/static/images/nandbank-lion-logo.png" : lionLogo.url);
  return <img src={url} alt="" aria-hidden="true" className={`${compact ? "h-10 w-9" : "h-12 w-10"} shrink-0 object-contain ${monochrome ? "brand-mark-black" : ""}`} />;
}

export function BrandLogo({ compact = false, tone = "dark" }: { compact?: boolean; tone?: "dark" | "light" }) {
  const wordmarkTone = tone === "dark" ? "text-ivory" : "text-charcoal";
  return (
    <Link to="/" aria-label="NandBank — página inicial" className="inline-flex min-w-0 items-center gap-3">
      <BrandMark compact={compact} monochrome={tone === "light"} />
      <span className={`min-w-0 font-display text-lg font-bold leading-none ${wordmarkTone}`}>NandBank</span>
    </Link>
  );
}
