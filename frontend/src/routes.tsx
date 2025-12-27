import { createBrowserRouter } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Dashboard from './pages/Dashboard';
import PriceTracking from './pages/PriceTracking';
import FlowAnalysis from './pages/FlowAnalysis';
import TradingSignals from './pages/TradingSignals';
import InvestorAttribution from './pages/InvestorAttribution';

export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <AppLayout />,
      children: [
        { index: true, element: <Dashboard /> },
        { path: 'prices', element: <PriceTracking /> },
        { path: 'flows', element: <FlowAnalysis /> },
        { path: 'signals', element: <TradingSignals /> },
        { path: 'attribution', element: <InvestorAttribution /> },
      ],
    },
  ],
  {
    future: {
      v7_startTransition: true,
    },
  }
);
