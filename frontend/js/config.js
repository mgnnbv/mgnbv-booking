export const API_BASE_URL = ["localhost", "127.0.0.1"].includes(location.hostname)
    ? `http://${location.hostname}:8000/api/v1`
    : "/api/v1";
