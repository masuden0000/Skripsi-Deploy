"use client"

import { Input } from "@/components/ui/input"
import { SearchIcon } from "@/components/icons/public-icons"

interface SearchInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

export function SearchInput({
  value,
  onChange,
  placeholder = "Cari...",
  className = "",
}: SearchInputProps) {
  return (
    <div className={`relative ${className}`}>
      <SearchIcon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
      <Input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-10 w-full rounded-lg border-gray-200 pl-10 pr-4 text-sm placeholder:text-gray-400 focus:border-pkm-400 focus:ring-1 focus:ring-pkm-400"
      />
    </div>
  )
}