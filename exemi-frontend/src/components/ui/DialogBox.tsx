import {useEffect, type CSSProperties, type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {MdClose} from 'react-icons/md';

export type DialogBoxProps = {
    open: boolean;
    onClose: () => void;
    children?: ReactNode;
    panelClassName?: string;
    panelStyle?: CSSProperties;
    'aria-label'?: string;
};

export function DialogBox({
    open,
    onClose,
    children,
    panelClassName = '',
    panelStyle,
    'aria-label': ariaLabel = 'Dialog',
}: DialogBoxProps) {
    useEffect(() => {
        if (!open) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [open, onClose]);

    if (!open || typeof document === 'undefined') return null;

    return createPortal(
        <div
            className="dialog-backdrop"
            role="presentation"
            aria-hidden={!open}
        >
            <div
                role="dialog"
                aria-modal="true"
                aria-label={ariaLabel}
                className={'dialog-panel ' + panelClassName}
                style={panelStyle}
            >
                <button
                    type="button"
                    className="dialog-close"
                    aria-label="Close"
                    onClick={onClose}
                >
                    <MdClose aria-hidden />
                </button>
                {children}
            </div>
        </div>,
        document.body,
    );
}
