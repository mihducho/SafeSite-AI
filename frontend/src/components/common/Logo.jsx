/** Biểu tượng SafeGate: mũ bảo hộ đơn giản trên nền tối (tự vẽ, không giống logo hãng nào). */
export function LogoMark({ size = 36 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <rect width="64" height="64" rx="14" fill="#1E293B" />
      <path d="M14 40a18 18 0 0 1 36 0z" fill="#F59E0B" />
      <rect x="29" y="19" width="6" height="21" rx="2" fill="#FCD34D" />
      <rect x="9" y="40" width="46" height="7" rx="3.5" fill="#FCD34D" />
    </svg>
  )
}

/** Logo + chữ SafeGate (dark = chữ trắng cho nền tối) */
export function Logo({ size = 36, dark = true, sub = 'Chấm công · Kiểm tra bảo hộ' }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 12 }}>
      <LogoMark size={size} />
      <span style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
        <b style={{ fontSize: 17, fontWeight: 700, color: dark ? '#fff' : '#0F172A', letterSpacing: '-0.01em' }}>SafeGate</b>
        {sub && <span style={{ fontSize: 12, color: dark ? '#94A3B8' : '#64748B' }}>{sub}</span>}
      </span>
    </span>
  )
}
