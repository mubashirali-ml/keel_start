/** The shared design system (ADR-0019, ADR-0035). Features import UI only from here. */
export { focusRing, focusRingInset } from "./focus";
export { Avatar, initials, type AvatarProps } from "./components/Avatar";
export { Badge, type BadgeProps, type BadgeTone } from "./components/Badge";
export { Button, buttonVariants, type ButtonProps } from "./components/Button";
export { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "./components/Card";
export { Checkbox, type CheckboxProps } from "./components/Checkbox";
export {
  ConfirmDialog,
  Dialog,
  DialogClose,
  DialogContent,
  DialogTrigger,
  type ConfirmDialogProps,
  type DialogContentProps,
} from "./components/Dialog";
export { FormField, useZodForm, type FormFieldProps } from "./components/FormField";
export { IconButton, type IconButtonProps } from "./components/IconButton";
export { Input, Textarea, type InputProps, type TextareaProps } from "./components/Input";
export { Label } from "./components/Label";
export { Markdown } from "./components/Markdown";
export { Menu, MenuContent, MenuGroup, MenuItem, MenuLabel, MenuSeparator, MenuTrigger } from "./components/Menu";
export {
  Banner,
  Countdown,
  TrustNote,
  type BannerProps,
  type BannerTone,
  type CountdownProps,
  type TrustNoteKind,
} from "./components/Notices";
export { PlanGate, isPlanRequired, planGateCopy, type PlanGateCopy, type PlanGateProps } from "./components/PlanGate";
export { Popover, PopoverClose, PopoverContent, PopoverTrigger } from "./components/Popover";
export { Progress, type ProgressProps } from "./components/Progress";
export { RadioGroup, type RadioGroupProps, type RadioOption } from "./components/RadioGroup";
export { SegmentedControl, type SegmentedControlProps, type SegmentedOption } from "./components/SegmentedControl";
export { Select, type SelectOption, type SelectProps } from "./components/Select";
export { Spinner } from "./components/Spinner";
export { EmptyState, ErrorState, LoadingBlock, Skeleton, type EmptyStateProps, type ErrorStateProps, type SkeletonProps } from "./components/States";
export { STATUS_STYLES, StatusBadge, type StatusBadgeProps } from "./components/StatusBadge";
export { Switch, type SwitchProps } from "./components/Switch";
export { Table, type TableColumn, type TableProps } from "./components/Table";
export { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/Tabs";
export { ToastProvider, useToast, type ToastOptions, type ToastTone } from "./components/Toast";
export { Tooltip, TooltipProvider, type TooltipProps } from "./components/Tooltip";
export { VisuallyHidden } from "./components/VisuallyHidden";
