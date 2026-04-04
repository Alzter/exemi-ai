import {useCallback, useEffect, useRef, useState, type RefObject} from 'react';
import { MdKeyboardArrowDown, MdKeyboardArrowUp } from 'react-icons/md';

const COLLAPSED_PX = 42;
const MIN_EXPANDED_PX = 160;
/** Default height when expanding before the user has resized (50% of viewport). */
const DEFAULT_EXPANDED_VIEWPORT_RATIO = 0.5;
const MAX_VIEWPORT_RATIO = 0.78;

function getDefaultExpandedHeightPx(): number {
    if (typeof window === 'undefined') return MIN_EXPANDED_PX;
    return window.innerHeight * DEFAULT_EXPANDED_VIEWPORT_RATIO;
}

function clamp(n: number, lo: number, hi: number) {
    return Math.min(hi, Math.max(lo, n));
}

type TasksWindowProps = {
    layoutContainerRef: RefObject<HTMLDivElement | null>;
};

export default function TasksWindow({layoutContainerRef}: TasksWindowProps) {
    const lastExpandedRef = useRef(getDefaultExpandedHeightPx());
    const [heightPx, setHeightPx] = useState(COLLAPSED_PX);
    const [dragging, setDragging] = useState(false);

    const dragStartY = useRef(0);
    const dragStartHeight = useRef(0);
    const activePointerId = useRef<number | null>(null);

    const open = heightPx > COLLAPSED_PX + 1;

    const maxForContainer = useCallback(() => {
        const el = layoutContainerRef.current;
        const h = el?.getBoundingClientRect().height ?? window.innerHeight;
        return Math.max(MIN_EXPANDED_PX, h * MAX_VIEWPORT_RATIO);
    }, [layoutContainerRef]);

    const endDrag = useCallback(() => {
        setDragging(false);
        activePointerId.current = null;
    }, []);

    useEffect(() => {
        if (!dragging) return;
        const onPointerMove = (e: PointerEvent) => {
            if (e.pointerId !== activePointerId.current) return;
            const delta = dragStartY.current - e.clientY;
            const maxH = maxForContainer();
            const next = clamp(dragStartHeight.current + delta, COLLAPSED_PX, maxH);
            setHeightPx(next);
            if (next > COLLAPSED_PX + 2) {
                lastExpandedRef.current = next;
            }
        };
        const onPointerUp = (e: PointerEvent) => {
            if (e.pointerId !== activePointerId.current) return;
            endDrag();
            setHeightPx((h) => {
                if (h <= COLLAPSED_PX + 12) {
                    return COLLAPSED_PX;
                }
                if (h < MIN_EXPANDED_PX) {
                    return MIN_EXPANDED_PX;
                }
                lastExpandedRef.current = h;
                return h;
            });
        };
        window.addEventListener('pointermove', onPointerMove);
        window.addEventListener('pointerup', onPointerUp);
        window.addEventListener('pointercancel', onPointerUp);
        return () => {
            window.removeEventListener('pointermove', onPointerMove);
            window.removeEventListener('pointerup', onPointerUp);
            window.removeEventListener('pointercancel', onPointerUp);
        };
    }, [dragging, endDrag, maxForContainer]);

    const onResizeHandlePointerDown = (e: React.PointerEvent) => {
        e.preventDefault();
        if (e.button !== 0) return;
        dragStartY.current = e.clientY;
        dragStartHeight.current = heightPx;
        activePointerId.current = e.pointerId;
        setDragging(true);
    };

    const toggleOpen = () => {
        if (dragging) return;
        setHeightPx((h) => {
            if (h > COLLAPSED_PX + 1) {
                lastExpandedRef.current = h;
                return COLLAPSED_PX;
            }
            const target = lastExpandedRef.current;
            const maxH = maxForContainer();
            return clamp(target, MIN_EXPANDED_PX, maxH);
        });
    };

    return (
        <div
            className={'tasks-panel' + (dragging ? ' tasks-panel--dragging' : '')}
            style={{height: heightPx}}
            aria-expanded={open}
        >
            <div
                className="tasks-panel-resize-handle"
                onPointerDown={onResizeHandlePointerDown}
                role="separator"
                aria-orientation="horizontal"
                aria-label="Resize tasks panel"
            />
            <button type="button" className="tasks-panel-header" onClick={toggleOpen}>
                <p>{open ? <MdKeyboardArrowDown /> : <MdKeyboardArrowUp />}Tasks</p>
                

            </button>
            <div className="tasks-panel-body">
                <p className="tasks-panel-placeholder">Task list will appear here.</p>
            </div>
        </div>
    );
}
