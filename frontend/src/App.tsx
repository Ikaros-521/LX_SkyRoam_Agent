import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import 'antd/dist/reset.css';
import './App.css';

import Layout from './components/Layout/Layout';
import HomePage from './pages/HomePage/HomePage';
import TravelPlanPage from './pages/TravelPlanPage/TravelPlanPage';
import PlanDetailPage from './pages/PlanDetailPage/PlanDetailPage';
import HistoryPage from './pages/HistoryPage/HistoryPage';
import AboutPage from './pages/AboutPage/AboutPage';
import TestPage from './pages/TestPage/TestPage';
import LoginPage from './pages/LoginPage/LoginPage';
import RegisterPage from './pages/RegisterPage/RegisterPage';
import RequireAdmin from './components/Auth/RequireAdmin';
import UsersAdminPage from './pages/Admin/UsersAdminPage';
import HistoryAdminPage from './pages/Admin/HistoryAdminPage';

const App: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <Router>
        <div className="App">
          <Layout>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/test" element={<TestPage />} />
              <Route path="/plan" element={<TravelPlanPage />} />
              <Route path="/plan/:id" element={<PlanDetailPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/admin/users" element={<RequireAdmin><UsersAdminPage /></RequireAdmin>} />
              <Route path="/admin/history" element={<RequireAdmin><HistoryAdminPage /></RequireAdmin>} />
            </Routes>
          </Layout>
        </div>
      </Router>
    </ConfigProvider>
  );
};

export default App;
