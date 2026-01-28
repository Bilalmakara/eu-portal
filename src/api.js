import axios from 'axios';

// Django'nun çalıştığı adres (8000 portu)
export const API_BASE_URL = "http://127.0.0.1:8000";

const api = axios.create({
    // Tüm API istekleri otomatik olarak /api ile başlar
    baseURL: API_BASE_URL + "/api",
});

export default api;