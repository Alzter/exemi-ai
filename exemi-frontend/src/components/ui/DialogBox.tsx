import {useEffect, type CSSProperties, type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {MdClose} from 'react-icons/md';

export type DialogBoxProps = {
    open: boolean;
    onClose: () => void;
    children?: ReactNode;
    /** Rendered to the left of the close control (e.g. overflow menu). */
    beforeClose?: ReactNode;
    /** When false, the default close (X) button is not shown. */
    showCloseButton?: boolean;
    /** When false, Escape is not handled here (parent may handle stacking). */
    closeOnEscape?: boolean;
    panelClassName?: string;
    panelStyle?: CSSProperties;
    backdropClassName?: string;
    'aria-label'?: string;
};

export function DialogBox({
    open,
    onClose,
    children,
    beforeClose,
    showCloseButton = true,
    closeOnEscape = true,
    panelClassName = '',
    panelStyle,
    backdropClassName = '',
    'aria-label': ariaLabel = 'Dialog',
}: DialogBoxProps) {
    useEffect(() => {
        if (!open || !closeOnEscape) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [open, onClose, closeOnEscape]);

    if (!open || typeof document === 'undefined') return null;

    return createPortal(
        <div
            className={'dialog-backdrop ' + backdropClassName}
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
                <div className="dialog-panel-top-actions">
                    {beforeClose}
                    {showCloseButton ? (
                        <button
                            type="button"
                            className="floating"
                            aria-label="Close"
                            onClick={onClose}
                        >
                            <MdClose aria-hidden />
                        </button>
                    ) : null}
                </div>
                {children}
            </div>
        </div>,
        document.body,
    );
}
