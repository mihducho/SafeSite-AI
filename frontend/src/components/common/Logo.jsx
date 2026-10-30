/** Biểu tượng SafeGate: mũ bảo hộ đơn giản trên nền tối (tự vẽ, không giống logo hãng nào). */
export function LogoMark({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <rect width="64" height="64" rx="8" fill="#18181B" stroke="#27272A" strokeWidth="2" />
      <path d="M14 40a18 18 0 0 1 36 0z" fill="#D97706" />
      <rect x="29" y="19" width="6" height="21" rx="1.5" fill="#F59E0B" />
      <rect x="9" y="40" width="46" height="7" rx="2" fill="#F59E0B" />
    </svg>
  )
}

/** Logo + chữ SafeGate (dark = chữ trắng cho nền tối) */
export function Logo({ size = 32, dark = true, sub = 'Chấm công · Kiểm tra bảo hộ' }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
      <LogoMark size={size} />
      <span style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
        <b style={{ fontSize: 15, fontWeight: 700, color: dark ? '#FAFAFA' : '#18181B', letterSpacing: '-0.02em' }}>SafeGate</b>
        {sub && <span style={{ fontSize: 11.5, color: dark ? '#71717A' : '#71717A' }}>{sub}</span>}
      </span>
    </span>
  )
}
