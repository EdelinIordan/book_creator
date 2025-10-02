import { ReactNode, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import clsx from "clsx";
import styles from "./Modal.module.css";

type ModalSize = "md" | "lg";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: ModalSize;
  bodyClassName?: string;
  footerClassName?: string;
  className?: string;
  initialFocusRef?: React.RefObject<HTMLElement>;
  closeLabel?: string;
}

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  size = "md",
  bodyClassName,
  footerClassName,
  className,
  initialFocusRef,
  closeLabel = "Close dialog",
}: ModalProps) {
  const [mounted, setMounted] = useState(false);
  const previousOverflowRef = useRef<string>();
  const titleId = useId();
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || !isOpen) {
      return;
    }

    previousOverflowRef.current = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflowRef.current ?? "";
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, mounted, onClose]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const elementToFocus = initialFocusRef?.current ?? closeButtonRef.current;
    elementToFocus?.focus({ preventScroll: true });
  }, [initialFocusRef, isOpen]);

  if (!mounted || !isOpen) {
    return null;
  }

  const sizeClass = size === "lg" ? styles.containerLarge : undefined;

  return createPortal(
    <div
      className={styles.overlay}
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className={clsx(styles.container, sizeClass, className)}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className={styles.header}>
          <h2 id={titleId} className={styles.title}>
            {title}
          </h2>
          <button
            type="button"
            className={styles.closeButton}
            onClick={onClose}
            aria-label={closeLabel}
            ref={closeButtonRef}
          >
            ×
          </button>
        </header>
        {description && <p className={styles.helper}>{description}</p>}
        <div className={clsx(styles.body, bodyClassName)}>{children}</div>
        {footer && <footer className={clsx(styles.footer, footerClassName)}>{footer}</footer>}
      </div>
    </div>,
    document.body
  );
}
