"use client"

import { useState } from "react"
import * as Popover from "@radix-ui/react-popover"
import { ChevronIcon } from "@/components/icons/public-icons"
import { cn } from "@/lib/utils"

type YearPickerProps = {
  value: string
  onChange: (year: string) => void
  placeholder?: string
  disabled?: boolean
  className?: string
}

function getYearRange(): number[] {
  const end = new Date().getFullYear() + 5
  const years: number[] = []
  for (let y = end; y >= 2000; y--) years.push(y)
  return years
}

const YEARS = getYearRange()

export function YearPicker({
  value,
  onChange,
  placeholder = "Pilih tahun",
  disabled = false,
  className,
}: YearPickerProps) {
  const [open, setOpen] = useState(false)

  function handleSelect(year: number) {
    onChange(String(year))
    setOpen(false)
  }

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild disabled={disabled}>
        <button
          type="button"
          className={cn(
            "flex h-9 w-full items-center justify-between rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm transition-colors",
            "hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-pkm-300 focus:ring-offset-0",
            "disabled:cursor-not-allowed disabled:opacity-50",
            value ? "text-gray-700" : "text-gray-400",
            className
          )}
        >
          <span>{value || placeholder}</span>
          <ChevronIcon open={open} className="size-4 shrink-0 text-gray-400" />
        </button>
      </Popover.Trigger>

      <Popover.Portal>
        <Popover.Content
          className="z-50 w-56 rounded-xl border border-gray-100 bg-white p-2.5 shadow-lg"
          sideOffset={6}
          align="start"
        >
          <div className="grid max-h-60 grid-cols-4 gap-1 overflow-y-auto">
            {YEARS.map((year) => (
              <button
                key={year}
                type="button"
                onClick={() => handleSelect(year)}
                className={cn(
                  "rounded-md px-1 py-2 text-center text-sm font-medium transition-colors",
                  String(year) === value
                    ? "bg-pkm-600 text-white"
                    : "text-gray-700 hover:bg-pkm-50 hover:text-pkm-700"
                )}
              >
                {year}
              </button>
            ))}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
