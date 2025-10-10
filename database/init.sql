-- 数据库初始化脚本
-- 创建必要的扩展和初始数据

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建初始用户数据
INSERT INTO users (username, email, full_name, hashed_password, is_verified, created_at, updated_at) 
VALUES 
('admin', 'admin@lxai.com', '系统管理员', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8f8f8f8f8f', true, NOW(), NOW()),
('demo_user', 'demo@lxai.com', '演示用户', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8f8f8f8f8f', true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- 创建初始目的地数据
INSERT INTO destinations (name, country, city, region, latitude, longitude, description, highlights, best_time_to_visit, popularity_score, safety_score, cost_level, created_at, updated_at)
VALUES 
('北京', '中国', '北京', '华北', 39.9042, 116.4074, '中华人民共和国的首都，历史文化名城', '["天安门广场", "故宫", "长城", "颐和园"]', '春季和秋季', 9.5, 9.0, 'medium', NOW(), NOW()),
('上海', '中国', '上海', '华东', 31.2304, 121.4737, '中国最大的经济中心城市', '["外滩", "东方明珠", "豫园", "南京路"]', '春季和秋季', 9.2, 8.8, 'high', NOW(), NOW()),
('广州', '中国', '广州', '华南', 23.1291, 113.2644, '广东省省会，岭南文化中心', '["珠江夜游", "陈家祠", "白云山", "上下九"]', '冬季和春季', 8.8, 8.5, 'medium', NOW(), NOW()),
('深圳', '中国', '深圳', '华南', 22.5431, 114.0579, '中国改革开放的前沿城市', '["世界之窗", "欢乐谷", "大梅沙", "华强北"]', '全年', 8.5, 8.7, 'high', NOW(), NOW()),
('杭州', '中国', '杭州', '华东', 30.2741, 120.1551, '人间天堂，西湖美景', '["西湖", "灵隐寺", "雷峰塔", "千岛湖"]', '春季和秋季', 9.0, 8.9, 'medium', NOW(), NOW())
ON CONFLICT (name, country) DO NOTHING;

-- 创建初始景点数据
INSERT INTO attractions (name, category, description, address, latitude, longitude, opening_hours, ticket_price, currency, rating, review_count, features, accessibility, contact_info, images, website, destination_id, created_at, updated_at)
VALUES 
('天安门广场', '历史建筑', '中华人民共和国的象征', '北京市东城区天安门广场', 39.9042, 116.4074, '{"周一": "全天开放", "周二": "全天开放", "周三": "全天开放", "周四": "全天开放", "周五": "全天开放", "周六": "全天开放", "周日": "全天开放"}', 0, 'CNY', 4.7, 12580, '["免费参观", "历史意义", "拍照圣地"]', '["无障碍通道", "轮椅租赁"]', '{"电话": "010-65132277"}', '["https://example.com/tiananmen1.jpg", "https://example.com/tiananmen2.jpg"]', 'https://www.tiananmen.org.cn', 1, NOW(), NOW()),
('故宫博物院', '博物馆', '明清两代的皇家宫殿', '北京市东城区景山前街4号', 39.9163, 116.3972, '{"周一": "08:30-17:00", "周二": "08:30-17:00", "周三": "08:30-17:00", "周四": "08:30-17:00", "周五": "08:30-17:00", "周六": "08:30-17:00", "周日": "08:30-17:00"}', 60, 'CNY', 4.8, 9876, '["世界文化遗产", "古建筑", "文物展览"]', '["无障碍通道", "语音导览"]', '{"电话": "010-85007421"}', '["https://example.com/gugong1.jpg", "https://example.com/gugong2.jpg"]', 'https://www.dpm.org.cn', 1, NOW(), NOW()),
('外滩', '观光景点', '上海的标志性景观', '上海市黄浦区中山东一路', 31.2397, 121.4994, '{"周一": "全天开放", "周二": "全天开放", "周三": "全天开放", "周四": "全天开放", "周五": "全天开放", "周六": "全天开放", "周日": "全天开放"}', 0, 'CNY', 4.6, 15678, '["免费参观", "夜景美丽", "历史建筑"]', '["无障碍通道"]', '{"电话": "021-63213579"}', '["https://example.com/waitan1.jpg", "https://example.com/waitan2.jpg"]', 'https://www.shanghai.gov.cn', 2, NOW(), NOW()),
('西湖', '自然景观', '人间天堂的美景', '浙江省杭州市西湖区', 30.2741, 120.1551, '{"周一": "全天开放", "周二": "全天开放", "周三": "全天开放", "周四": "全天开放", "周五": "全天开放", "周六": "全天开放", "周日": "全天开放"}', 0, 'CNY', 4.9, 23456, '["免费参观", "自然美景", "文化底蕴"]', '["无障碍通道", "游船服务"]', '{"电话": "0571-87969691"}', '["https://example.com/xihu1.jpg", "https://example.com/xihu2.jpg"]', 'https://www.hangzhou.gov.cn', 5, NOW(), NOW())
ON CONFLICT (name, destination_id) DO NOTHING;

-- 创建初始餐厅数据
INSERT INTO restaurants (name, cuisine_type, description, address, latitude, longitude, opening_hours, price_range, rating, review_count, features, contact_info, menu_highlights, images, website, destination_id, created_at, updated_at)
VALUES 
('全聚德烤鸭店', '北京菜', '百年老字号烤鸭店', '北京市东城区前门大街30号', 39.9042, 116.4074, '{"周一": "11:00-22:00", "周二": "11:00-22:00", "周三": "11:00-22:00", "周四": "11:00-22:00", "周五": "11:00-22:00", "周六": "11:00-22:00", "周日": "11:00-22:00"}', '$$$', 4.5, 5678, '["传统老字号", "适合聚餐", "有包间"]', '{"电话": "010-65112418", "地址": "北京市东城区前门大街30号"}', '["北京烤鸭", "炸酱面", "豆汁"]', '["https://example.com/quanjude1.jpg", "https://example.com/quanjude2.jpg"]', 'https://www.quanjude.com.cn', 1, NOW(), NOW()),
('小笼包店', '上海菜', '正宗上海小笼包', '上海市黄浦区南京东路123号', 31.2304, 121.4737, '{"周一": "10:00-22:00", "周二": "10:00-22:00", "周三": "10:00-22:00", "周四": "10:00-22:00", "周五": "10:00-22:00", "周六": "10:00-22:00", "周日": "10:00-22:00"}', '$$', 4.3, 3456, '["传统小吃", "价格实惠", "外卖服务"]', '{"电话": "021-63212345", "地址": "上海市黄浦区南京东路123号"}', '["小笼包", "生煎包", "糖醋排骨"]', '["https://example.com/xiaolongbao1.jpg", "https://example.com/xiaolongbao2.jpg"]', 'https://www.xiaolongbao.com', 2, NOW(), NOW()),
('粤菜馆', '粤菜', '正宗广东菜', '广东省广州市天河区珠江新城', 23.1291, 113.2644, '{"周一": "11:00-23:00", "周二": "11:00-23:00", "周三": "11:00-23:00", "周四": "11:00-23:00", "周五": "11:00-23:00", "周六": "11:00-23:00", "周日": "11:00-23:00"}', '$$$', 4.7, 7890, '["正宗粤菜", "环境优雅", "服务周到"]', '{"电话": "020-12345678", "地址": "广东省广州市天河区珠江新城"}', '["白切鸡", "叉烧", "煲仔饭"]', '["https://example.com/yuecai1.jpg", "https://example.com/yuecai2.jpg"]', 'https://www.yuecai.com', 3, NOW(), NOW())
ON CONFLICT (name, destination_id) DO NOTHING;

-- 创建初始活动类型数据
INSERT INTO activity_types (name, description, category, duration_range, difficulty_level, age_restriction, created_at, updated_at)
VALUES 
('观光游览', '参观景点和地标建筑', 'cultural', '{"min": 2, "max": 8}', 'easy', '{"min": 0, "max": 100}', NOW(), NOW()),
('户外运动', '登山、徒步等户外活动', 'outdoor', '{"min": 4, "max": 12}', 'medium', '{"min": 8, "max": 65}', NOW(), NOW()),
('文化体验', '博物馆、艺术馆参观', 'cultural', '{"min": 1, "max": 6}', 'easy', '{"min": 0, "max": 100}', NOW(), NOW()),
('美食体验', '品尝当地特色美食', 'food', '{"min": 1, "max": 3}', 'easy', '{"min": 0, "max": 100}', NOW(), NOW()),
('购物娱乐', '购物和娱乐活动', 'entertainment', '{"min": 2, "max": 6}', 'easy', '{"min": 0, "max": 100}', NOW(), NOW())
ON CONFLICT (name) DO NOTHING;

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_travel_plans_user_id ON travel_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_travel_plans_status ON travel_plans(status);
CREATE INDEX IF NOT EXISTS idx_travel_plans_destination ON travel_plans(destination);
CREATE INDEX IF NOT EXISTS idx_travel_plans_created_at ON travel_plans(created_at);

CREATE INDEX IF NOT EXISTS idx_destinations_name ON destinations(name);
CREATE INDEX IF NOT EXISTS idx_destinations_country ON destinations(country);
CREATE INDEX IF NOT EXISTS idx_destinations_popularity ON destinations(popularity_score);

CREATE INDEX IF NOT EXISTS idx_attractions_destination_id ON attractions(destination_id);
CREATE INDEX IF NOT EXISTS idx_attractions_category ON attractions(category);
CREATE INDEX IF NOT EXISTS idx_attractions_rating ON attractions(rating);

CREATE INDEX IF NOT EXISTS idx_restaurants_destination_id ON restaurants(destination_id);
CREATE INDEX IF NOT EXISTS idx_restaurants_cuisine_type ON restaurants(cuisine_type);
CREATE INDEX IF NOT EXISTS idx_restaurants_rating ON restaurants(rating);

-- 创建全文搜索索引
CREATE INDEX IF NOT EXISTS idx_destinations_search ON destinations USING gin(to_tsvector('chinese', name || ' ' || description));
CREATE INDEX IF NOT EXISTS idx_attractions_search ON attractions USING gin(to_tsvector('chinese', name || ' ' || description));
CREATE INDEX IF NOT EXISTS idx_restaurants_search ON restaurants USING gin(to_tsvector('chinese', name || ' ' || description));
