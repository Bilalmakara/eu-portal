import axios from 'axios';

// Django'nun çalıştığı adres (8000 portu)
export const API_BASE_URL = "";

const api = axios.create({
    // Tüm API istekleri otomatik olarak /api ile başlar
    baseURL: API_BASE_URL + "/api",
});

export default api;
