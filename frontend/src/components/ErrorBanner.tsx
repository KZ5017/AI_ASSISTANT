import { X } from "lucide-react";

type ErrorBannerProps = {
  message: string;
  onClose: () => void;
};

export function ErrorBanner({ message, onClose }: ErrorBannerProps) {
  return <div className="error-banner" role="alert">{message}<button type="button" aria-label="Hiba bezárása" onClick={onClose}><X size={16} aria-hidden="true" /></button></div>;
}
