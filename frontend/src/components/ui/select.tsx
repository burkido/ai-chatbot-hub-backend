import React, { createContext, forwardRef, useContext, useId } from 'react';
import { cn } from '@/utils';

const SelectContext = createContext<{
  value?: string;
  onValueChange?: (value: string) => void;
}>({});

export interface SelectProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: string;
  onValueChange?: (value: string) => void;
}

const Select = React.forwardRef<HTMLDivElement, SelectProps>(
  ({ className, value, onValueChange, children, ...props }, ref) => {
    return (
      <SelectContext.Provider value={{ value, onValueChange }}>
        <div ref={ref} className={cn('relative', className)} {...props}>
          {children}
        </div>
      </SelectContext.Provider>
    );
  }
);
Select.displayName = 'Select';

export interface SelectTriggerProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

const SelectTrigger = forwardRef<HTMLButtonElement, SelectTriggerProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'flex h-10 w-full items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-900',
          className
        )}
        type="button"
        {...props}
      >
        {children}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-4 w-4 opacity-50"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>
    );
  }
);
SelectTrigger.displayName = 'SelectTrigger';

export interface SelectValueProps {
  placeholder?: string;
}

const SelectValue = ({ placeholder }: SelectValueProps) => {
  const { value } = useContext(SelectContext);
  return <span>{value || placeholder}</span>;
};
SelectValue.displayName = 'SelectValue';

export interface SelectContentProps
  extends React.HTMLAttributes<HTMLDivElement> {}

const SelectContent = forwardRef<HTMLDivElement, SelectContentProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md border border-gray-300 bg-white py-1 text-sm shadow-md dark:border-gray-700 dark:bg-gray-900',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);
SelectContent.displayName = 'SelectContent';

export interface SelectItemProps
  extends React.LiHTMLAttributes<HTMLLIElement> {
  value: string;
}

const SelectItem = forwardRef<HTMLLIElement, SelectItemProps>(
  ({ className, children, value, ...props }, ref) => {
    const id = useId();
    const { value: selectedValue, onValueChange } = useContext(SelectContext);
    const isSelected = selectedValue === value;

    return (
      <li
        ref={ref}
        className={cn(
          'relative flex cursor-pointer select-none items-center py-1.5 pl-8 pr-2 hover:bg-gray-100 dark:hover:bg-gray-800',
          isSelected && 'bg-gray-100 dark:bg-gray-800',
          className
        )}
        role="option"
        aria-selected={isSelected}
        id={id}
        data-value={value}
        onClick={() => onValueChange && onValueChange(value)}
        {...props}
      >
        {isSelected && (
          <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-4 w-4"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </span>
        )}
        <span className="truncate">{children}</span>
      </li>
    );
  }
);
SelectItem.displayName = 'SelectItem';

export { Select, SelectContent, SelectTrigger, SelectValue, SelectItem };