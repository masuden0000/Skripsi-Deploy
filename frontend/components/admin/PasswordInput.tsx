"use client"

import { useState } from "react"
import Image from "next/image"
import { Input } from "@/components/ui/input"
import { EyeOffIcon, EyeIcon } from "@/components/icons/public-icons"

interface PasswordInputProps {
  id?: string
  name?: string
  value?: string
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
  placeholder?: string
  required?: boolean
  disabled?: boolean
  className?: string
  showLockIcon?: boolean
}

export function PasswordInput({
  id,
  name,
  value,
  onChange,
  placeholder = "Masukkan password",
  required = false,
  disabled = false,
  className = "",
  showLockIcon = false,
}: PasswordInputProps) {
  const [showPassword, setShowPassword] = useState(false)

  return (
    <div className={`relative ${className}`}>
      {showLockIcon && (
        <Image
          src="/icon-lock.svg"
          alt=""
          width={20}
          height={20}
          aria-hidden
          className="pointer-events-none absolute left-3 top-1/2 z-10 -translate-y-1/2"
        />
      )}
      <Input
        id={id}
        name={name}
        type={showPassword ? "text" : "password"}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        className={`h-11 rounded-lg border-pkm-400 pr-10 text-sm placeholder:text-gray-400 focus-visible:ring-pkm-600 ${showLockIcon ? "pl-10" : ""}`}
      />
      <button
        type="button"
        onClick={() => setShowPassword(!showPassword)}
        className={`absolute top-1/2 -translate-y-1/2 text-gray-400 transition-colors hover:text-gray-600 ${showLockIcon ? "right-3" : "right-3"}`}
        tabIndex={-1}
        aria-label={showPassword ? "Sembunyikan password" : "Tampilkan password"}
      >
        {showPassword ? (
          <EyeOffIcon className="size-4" />
        ) : (
          <EyeIcon className="size-4" />
        )}
      </button>
    </div>
  )
}