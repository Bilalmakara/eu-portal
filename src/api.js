import axios from 'axios';

// ARTIK BACKEND ADRESİNİ TAM OLARAK YAZIYORUZ
// Çünkü Frontend ve Backend ayrı evlerde yaşayacaklar.
export const API_BASE_URL = "https://eu-portal.onrender.com"; 

const api = axios.create({
    baseURL: API_BASE_URL + "/api",
});

export default api;
