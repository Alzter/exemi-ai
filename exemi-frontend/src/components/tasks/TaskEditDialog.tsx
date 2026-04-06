import {DialogBox} from '../ui/DialogBox';

export type TaskEditDialogProps = {
    open: boolean;
    onClose: () => void;
    /** Same background as the To-Do task row (`safeTaskBackgroundFromColourRaw`). */
    backgroundColor: string;
};

export function TaskEditDialog({open, onClose, backgroundColor}: TaskEditDialogProps) {
    return (
        <DialogBox
            open={open}
            onClose={onClose}
            aria-label="Edit task"
            panelClassName="task-edit-dialog-panel"
            panelStyle={{
                width: 'min(650px, calc(100vw - 2rem))',
                height: 'min(500px, calc(100vh - 2rem))',
                borderRadius: 8,
                backgroundColor,
            }}
        />
    );
}
