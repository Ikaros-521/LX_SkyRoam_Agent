import React, { useState } from 'react';
import { Button, Space, Select, Typography, Modal, Image, Alert } from 'antd';
import { EnvironmentOutlined, ExportOutlined, GlobalOutlined, PictureOutlined, WarningOutlined } from '@ant-design/icons';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MAP_CONFIG, MapProvider, MapMode } from '../../config/map';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';

const { Text, Title } = Typography;
const { Option } = Select;

// 修复 Leaflet 默认图标问题
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

interface MapComponentProps {
  destination?: string;
  latitude?: number;
  longitude?: number;
  title?: string;
}

const MapComponent: React.FC<MapComponentProps> = ({
  destination = '目的地',
  latitude = 39.9042,
  longitude = 116.4074,
  title = '目的地地图'
}) => {
  const [mapType, setMapType] = useState<MapMode>('static');
  const [showExternalModal, setShowExternalModal] = useState(false);
  const [imageError, setImageError] = useState(false);

  // 地图瓦片层选项
  const tileLayerOptions = {
    openstreetmap: {
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '© OpenStreetMap contributors'
    },
    cartodb: {
      url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
      attribution: '© OpenStreetMap contributors © CARTO'
    },
    satellite: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attribution: 'Tiles © Esri'
    }
  };

  const [currentTileLayer, setCurrentTileLayer] = useState('openstreetmap');
  const [staticMapProvider, setStaticMapProvider] = useState<MapProvider>('amap');

  // 生成静态地图URL（通过后端代理）
  const generateStaticMapUrl = (
    provider: MapProvider,
    longitude: number,
    latitude: number,
    zoom: number = MAP_CONFIG.DEFAULT.ZOOM,
    width: number = MAP_CONFIG.DEFAULT.WIDTH,
    height: number = MAP_CONFIG.DEFAULT.HEIGHT,
    title?: string
  ): string => {
    const params = new URLSearchParams({
      provider,
      longitude: longitude.toString(),
      latitude: latitude.toString(),
      zoom: zoom.toString(),
      width: width.toString(),
      height: height.toString(),
    });
    
    if (title) {
      params.append('title', title);
    }
    
    return `${buildApiUrl(API_ENDPOINTS.MAP_STATIC)}?${params.toString()}`;
  };

  // 跳转到外部地图
  const openExternalMap = (mapProvider: string) => {
    const { EXTERNAL } = MAP_CONFIG;
    const encodedDestination = encodeURIComponent(destination);
    let url = '';

    switch (mapProvider) {
      case 'amap':
        // 高德地图
        url = `${EXTERNAL.AMAP_WEB_URL}?position=${longitude},${latitude}&name=${encodedDestination}&src=myapp`;
        break;
      case 'baidu':
        // 百度地图
        url = `${EXTERNAL.BAIDU_WEB_URL}?location=${latitude},${longitude}&title=${encodedDestination}&content=${encodedDestination}&output=html&src=webapp.baidu.openAPIdemo`;
        break;
      case 'google':
        // Google 地图
        url = `${EXTERNAL.GOOGLE_WEB_URL}?api=1&query=${latitude},${longitude}`;
        break;
      case 'tencent':
        // 腾讯地图
        url = `${EXTERNAL.TENCENT_WEB_URL}?marker=coord:${latitude},${longitude};title:${encodedDestination}&referer=myapp`;
        break;
      default:
        return;
    }

    window.open(url, '_blank');
    setShowExternalModal(false);
  };

  // 渲染静态地图
  const renderStaticMap = () => {
    const staticMapUrl = generateStaticMapUrl(
      staticMapProvider, 
      longitude, 
      latitude, 
      MAP_CONFIG.DEFAULT.ZOOM,
      MAP_CONFIG.DEFAULT.WIDTH,
      MAP_CONFIG.DEFAULT.HEIGHT,
      destination
    );
    
    return (
      <div style={{ width: '100%' }}>
        <div style={{ marginBottom: '12px' }}>
          <Space>
            <Text type="secondary">地图提供商：</Text>
            <Select
              value={staticMapProvider}
              onChange={(value) => {
                setStaticMapProvider(value);
                setImageError(false);
              }}
              size="small"
              style={{ width: 100 }}
            >
              <Option value="amap">高德地图</Option>
              {/* <Option value="baidu">百度地图</Option> */}
            </Select>
          </Space>
        </div>

        <div style={{ 
          width: '100%',
          background: '#f5f5f5',
          borderRadius: '8px',
          padding: '16px',
          position: 'relative'
        }}>
          {/* 静态地图图片 */}
          {!imageError ? (
            <div style={{ 
              width: '100%', 
              height: '300px', 
              marginBottom: '20px',
              borderRadius: '6px',
              overflow: 'hidden',
              background: '#fff',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Image
                src={staticMapUrl}
                alt={`${destination}地图`}
                style={{ 
                  maxWidth: '100%', 
                  maxHeight: '100%',
                  objectFit: 'contain',
                }}
                onError={() => setImageError(true)}
                fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMIAAADDCAYAAADQvc6UAAABRWlDQ1BJQ0MgUHJvZmlsZQAAKJFjYGASSSwoyGFhYGDIzSspCnJ3UoiIjFJgf8LAwSDCIMogwMCcmFxc4BgQ4ANUwgCjUcG3awyMIPqyLsis7PPOq3QdDFcvjV3jOD1boQVTPQrgSkktTgbSf4A4LbmgqISBgTEFyFYuLykAsTuAbJEioKOA7DkgdjqEvQHEToKwj4DVhAQ5A9k3gGyB5IxEoBmML4BsnSQk8XQkNtReEOBxcfXxUQg1Mjc0dyHgXNJBSWpFCYh2zi+oLMpMzyhRcASGUqqCZ16yno6CkYGRAQMDKMwhqj/fAIcloxgHQqxAjIHBEugw5sUIsSQpBobtQPdLciLEVJYzMPBHMDBsayhILEqEO4DxG0txmrERhM29nYGBddr//5/DGRjYNRkY/l7////39v///y4Dmn+LgeHANwDrkl1AuO+pmgAAADhlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAAqACAAQAAAABAAAAwqADAAQAAAABAAAAwwAAAAD9b/HnAAAHlklEQVR4Ae3dP3Ik1RnG4W+FgYxN"
                preview={false}
              />
            </div>
          ) : (
            <div style={{ 
              width: '100%', 
              height: '300px', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              marginBottom: '20px',
              border: '2px dashed #d9d9d9',
              borderRadius: '6px',
              background: '#fafafa'
            }}>
              <Space direction="vertical" style={{ textAlign: 'center' }}>
                 <PictureOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
                 <Text type="secondary">
                   地图加载失败，请检查网络连接
                 </Text>
               </Space>
            </div>
          )}
          
          {/* 地图信息和操作按钮 */}
          <div style={{ textAlign: 'center' }}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <div>
                <Text strong style={{ fontSize: '16px', color: '#1890ff' }}>{destination}</Text>
                <br />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  坐标：{latitude}, {longitude}
                </Text>
              </div>
              <Space wrap size="middle">
                <Button 
                  type="primary" 
                  icon={<ExportOutlined />}
                  onClick={() => openExternalMap('amap')}
                  size="large"
                >
                  高德导航
                </Button>
                <Button 
                  icon={<ExportOutlined />}
                  onClick={() => openExternalMap('baidu')}
                  size="large"
                >
                  百度导航
                </Button>
              </Space>
            </Space>
          </div>
        </div>
      </div>
    );
  };

  const renderLeafletMap = () => (
    <div style={{ height: '300px', width: '100%' }}>
      <div style={{ marginBottom: '8px' }}>
        <Space>
          <Text type="secondary">地图样式：</Text>
          <Select
            value={currentTileLayer}
            onChange={setCurrentTileLayer}
            size="small"
            style={{ width: 120 }}
          >
            <Option value="openstreetmap">标准地图</Option>
            <Option value="cartodb">简洁地图</Option>
            <Option value="satellite">卫星地图</Option>
          </Select>
        </Space>
      </div>
      <MapContainer
        center={[latitude, longitude]}
        zoom={13}
        style={{ height: '100%', width: '100%', borderRadius: '6px' }}
      >
        <TileLayer
          url={tileLayerOptions[currentTileLayer as keyof typeof tileLayerOptions].url}
          attribution={tileLayerOptions[currentTileLayer as keyof typeof tileLayerOptions].attribution}
        />
        <Marker position={[latitude, longitude]}>
          <Popup>
            <div>
              <strong>{destination}</strong>
              <br />
              纬度: {latitude}
              <br />
              经度: {longitude}
            </div>
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  );

  const renderExternalOptions = () => (
    <div style={{ 
      textAlign: 'center', 
      padding: '40px 20px',
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      borderRadius: '8px',
      minHeight: '300px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center'
    }}>
      <Space direction="vertical" size="large">
        <div>
          <EnvironmentOutlined style={{ 
            fontSize: '64px', 
            color: '#1890ff', 
            marginBottom: '16px',
            textShadow: '0 2px 4px rgba(24,144,255,0.3)'
          }} />
          <Title level={3} style={{ margin: '16px 0 8px 0', color: '#262626' }}>
            {destination}
          </Title>
          <Text type="secondary" style={{ fontSize: '16px' }}>
            坐标：{latitude}, {longitude}
          </Text>
        </div>
        
        <div style={{ marginTop: '32px' }}>
          <Text style={{ 
            fontSize: '16px', 
            color: '#595959', 
            marginBottom: '24px',
            display: 'block'
          }}>
            选择地图应用进行导航
          </Text>
          <Space wrap size="middle" style={{ justifyContent: 'center' }}>
            <Button 
              type="primary" 
              size="large"
              icon={<ExportOutlined />}
              onClick={() => openExternalMap('amap')}
              style={{ 
                height: '48px',
                borderRadius: '24px',
                paddingLeft: '24px',
                paddingRight: '24px',
                fontSize: '16px',
                boxShadow: '0 4px 12px rgba(24,144,255,0.3)'
              }}
            >
              高德地图导航
            </Button>
            <Button 
              size="large"
              icon={<ExportOutlined />}
              onClick={() => openExternalMap('baidu')}
              style={{ 
                height: '48px',
                borderRadius: '24px',
                paddingLeft: '24px',
                paddingRight: '24px',
                fontSize: '16px',
                borderColor: '#1890ff',
                color: '#1890ff'
              }}
            >
              百度地图导航
            </Button>
            <Button 
              size="large"
              icon={<ExportOutlined />}
              onClick={() => openExternalMap('google')}
              style={{ 
                height: '48px',
                borderRadius: '24px',
                paddingLeft: '24px',
                paddingRight: '24px',
                fontSize: '16px',
                borderColor: '#52c41a',
                color: '#52c41a'
              }}
            >
              Google Maps
            </Button>
            <Button 
              size="large"
              icon={<ExportOutlined />}
              onClick={() => openExternalMap('tencent')}
              style={{ 
                height: '48px',
                borderRadius: '24px',
                paddingLeft: '24px',
                paddingRight: '24px',
                fontSize: '16px',
                borderColor: '#722ed1',
                color: '#722ed1'
              }}
            >
              腾讯地图导航
            </Button>
          </Space>
        </div>
      </Space>
    </div>
  );

  return (
    <div style={{ 
      padding: '16px', 
      background: '#fff', 
      borderRadius: '8px', 
      boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      border: '1px solid #f0f0f0',
      width: '100%'
    }}>
      <div style={{ 
        marginBottom: '20px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        paddingBottom: '16px',
        borderBottom: '1px solid #f0f0f0'
      }}>
        <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
           <EnvironmentOutlined style={{ marginRight: '8px' }} />
           目的地地图
         </Title>
        <Select
          value={mapType}
          onChange={setMapType}
          style={{ width: 140 }}
          size="large"
        >
          <Option value="static">
            <PictureOutlined style={{ marginRight: '6px' }} />
            静态地图
          </Option>
          <Option value="leaflet">
            <GlobalOutlined style={{ marginRight: '6px' }} />
            交互地图
          </Option>
          <Option value="external">
            <ExportOutlined style={{ marginRight: '6px' }} />
            外部导航
          </Option>
        </Select>
      </div>

      <div style={{ minHeight: '400px' }}>
        {mapType === 'static' && renderStaticMap()}
        {mapType === 'leaflet' && renderLeafletMap()}
        {mapType === 'external' && renderExternalOptions()}
      </div>
      
      {/* 外部地图选择模态框 */}
      <Modal
        title="选择地图应用"
        open={showExternalModal}
        onCancel={() => setShowExternalModal(false)}
        footer={null}
        width={400}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Button 
            block 
            size="large"
            icon={<ExportOutlined />}
            onClick={() => openExternalMap('amap')}
          >
            高德地图
          </Button>
          <Button 
            block 
            size="large"
            icon={<ExportOutlined />}
            onClick={() => openExternalMap('baidu')}
          >
            百度地图
          </Button>
          <Button 
            block 
            size="large"
            icon={<ExportOutlined />}
            onClick={() => openExternalMap('google')}
          >
            Google地图
          </Button>
          <Button 
            block 
            size="large"
            icon={<ExportOutlined />}
            onClick={() => openExternalMap('tencent')}
          >
            腾讯地图
          </Button>
        </Space>
      </Modal>
    </div>
  );
};

export default MapComponent;