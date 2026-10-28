import { useState, useCallback } from "react";
import { Search, Github } from "lucide-react";
import { clsx } from "clsx";

interface UsernameInputProps {
  onSubmit: (username: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function UsernameInput({ onSubmit, disabled, placeholder = "Enter GitHub username or URL" }: UsernameInputProps) {
  const [value, setValue] = useState("");

  const extractUsername = useCallback((input: string): string => {
    const trimmed = input.trim();
    const urlMatch = trimmed.match(/github\.com\/([^/?#]+)/i);
    return urlMatch ? urlMatch[1] : trimmed;
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const username = extractUsername(value);
    if (username) {
      onSubmit(username);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="relative flex-1">
        <label htmlFor="username" className="sr-only">GitHub username or URL</label>
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
          <Github className="w-5 h-5" />
        </div>
        <input
          id="username"
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className={clsx(
            "w-full pl-10 pr-4 py-2.5",
            "bg-card border border-border rounded-lg",
            "text-text placeholder-muted",
            "focus:outline-none focus:ring-2 focus:ring-primary",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "transition-colors"
          )}
        />
      </div>
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className={clsx(
          "px-6 py-2.5",
          "bg-primary text-white rounded-lg font-medium",
          "hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-bg",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "transition-colors",
          "flex items-center gap-2"
        )}
      >
        <Search className="w-4 h-4" />
        Lookup
      </button>
    </form>
  );
}