import React from 'react';
import { Routes, Route } from 'react-router-dom';
import RequireAdmin from '../../components/Auth/RequireAdmin';
import HomePage from '../../pages/HomePage/HomePage';
import TravelPlanPage from '../../pages/TravelPlanPage/TravelPlanPage';
import PlanDetailPage from '../../pages/PlanDetailPage/PlanDetailPage';
import AboutPage from '../../pages/AboutPage/AboutPage';
import TestPage from '../../pages/TestPage/TestPage';
import LoginPage from '../../pages/LoginPage/LoginPage';
import RegisterPage from '../../pages/RegisterPage/RegisterPage';
import UsersAdminPage from '../../pages/Admin/UsersAdminPage';
import HistoryAdminPage from '../../pages/Admin/HistoryAdminPage';
import DestinationsPage from '../../pages/DestinationsPage/DestinationsPage';
import PlansLibraryPage from '../../pages/PlansLibraryPage/PlansLibraryPage';
import PlanEditPage from '../../pages/PlanEditPage/PlanEditPage';

const RouterApp: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/test" element={<TestPage />} />
      <Route path="/plan" element={<TravelPlanPage />} />
      <Route path="/plan/:id" element={<PlanDetailPage />} />
      <Route path="/plans" element={<PlansLibraryPage />} />
      <Route path="/history" element={<PlansLibraryPage />} />
      <Route path="/destinations" element={<DestinationsPage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/admin/users" element={<RequireAdmin><UsersAdminPage /></RequireAdmin>} />
      <Route path="/admin/history" element={<RequireAdmin><HistoryAdminPage /></RequireAdmin>} />
      <Route path="/plan/:id/edit" element={<RequireAdmin><PlanEditPage /></RequireAdmin>} />
    </Routes>
  );
};

export default RouterApp;