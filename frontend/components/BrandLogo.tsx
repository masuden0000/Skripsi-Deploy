"use client"

import NextImage from "next/image"

interface BrandLogoProps {
  size?: number
  invert?: boolean
  priority?: boolean
  className?: string
}

export default function BrandLogo({ size = 80, invert = false, priority = false, className = "" }: BrandLogoProps) {
  return (
    <NextImage
      src="/logo-upnvj.png"
      alt="Logo UPNVJ"
      width={size}
      height={size}
      className={"object-contain" + (invert ? " brightness-0 invert" : " mb-2") + (className ? " " + className : "")}
      priority={priority}
    />
  )
}
