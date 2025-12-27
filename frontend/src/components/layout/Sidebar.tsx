import { NavLink } from 'react-router-dom';
import {
  BarChart3,
  TrendingUp,
  Signal,
  Users,
  LayoutDashboard
} from 'lucide-react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/prices', label: 'Price Tracking', icon: TrendingUp },
  { path: '/flows', label: 'Flow Analysis', icon: BarChart3 },
  { path: '/signals', label: 'Trading Signals', icon: Signal },
  { path: '/attribution', label: 'Investor Attribution', icon: Users },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen">
      <nav className="p-4 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-600'
                  : 'text-gray-700 hover:bg-gray-50'
              }`
            }
          >
            <item.icon size={20} />
            <span className="font-medium">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
