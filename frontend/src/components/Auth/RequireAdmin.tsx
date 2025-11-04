import React from 'react';
import { Spin, message } from 'antd';
import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getToken, authFetch } from '../../utils/auth';
import { buildApiUrl } from '../../config/api';

interface Props {
  children: React.ReactNode;
}

const RequireAdmin: React.FC<Props> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    const checkAdmin = async () => {
      const token = getToken();
      if (!token) {
        navigate('/login');
        return;
      }
      try {
        const res = await authFetch(buildApiUrl('/users/me'));
        if (!res.ok) {
          navigate('/login');
          return;
        }
        const me = await res.json();
        if (me?.role === 'admin') {
          setAuthorized(true);
        } else {
          message.warning('仅管理员可访问该页面');
          navigate('/');
        }
      } catch (e) {
        navigate('/login');
      } finally {
        setLoading(false);
      }
    };
    checkAdmin();
  }, [location.pathname]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '48px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!authorized) return null;
  return <>{children}</>;
};

export default RequireAdmin;