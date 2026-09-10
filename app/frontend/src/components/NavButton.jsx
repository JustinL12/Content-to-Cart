import { Link, useLocation } from 'react-router-dom'

export default function NavButton() {
  const location = useLocation()
  const isInput = location.pathname === '/input' || location.pathname === '/'
  const to = isInput ? '/ingredients' : '/input'
  const label = isInput ? 'Go to Ingredient Manager' : 'Go to Recipe Input'
  const icon = isInput ? '≡' : '←' // list / back

  return (
    <Link
      to={to}
      className="nav-button"
      aria-label={label}
      title={label}
    >
      {icon}
    </Link>
  )
}
