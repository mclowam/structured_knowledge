import styles from './PencilProgress.module.css'

type PencilProgressProps = {
  progress: number
  label?: string
  status?: string
  className?: string
}

export function PencilProgress({
  progress,
  label = 'Progress',
  status,
  className,
}: PencilProgressProps) {
  const value = Number.isNaN(progress) ? 0 : Math.min(100, Math.max(0, progress))

  return (
    <span
      className={[styles.progress, className].filter(Boolean).join(' ')}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
      aria-valuetext={status}
    >
      <svg viewBox="0 0 200 16" preserveAspectRatio="none" aria-hidden="true" focusable="false">
        <path className={styles.track} d="M 3 9 C 38 7, 64 10, 99 8 S 166 7, 197 8" />
        <path
          className={styles.stroke}
          d="M 3 9 C 38 7, 64 10, 99 8 S 166 7, 197 8"
          pathLength={100}
          strokeDasharray={100}
          strokeDashoffset={100 - value}
        />
      </svg>
    </span>
  )
}
