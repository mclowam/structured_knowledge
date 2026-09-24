import { createElement } from 'react'
import type { ComponentPropsWithoutRef } from 'react'
import styles from './PaperCard.module.css'

type PaperCardElement = 'div' | 'form' | 'li'

type PaperCardProps<T extends PaperCardElement> = {
  as?: T
  className?: string
} & Omit<ComponentPropsWithoutRef<T>, 'as' | 'className'>

export function PaperCard<T extends PaperCardElement = 'div'>({
  as,
  className,
  ...props
}: PaperCardProps<T>) {
  const Component = as ?? 'div'
  const cardClassName = [styles.card, className].filter(Boolean).join(' ')

  return createElement(Component, { ...props, className: cardClassName })
}
