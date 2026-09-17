function csrfToken(documentRef = document) {
  return documentRef.cookie.split("; ").find((value) => value.startsWith("csrftoken="))?.split("=")[1] || "";
}

export async function requestJson(url, options = {}, documentRef = document) {
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: { "X-CSRFToken": csrfToken(documentRef), Accept: "application/json", ...options.headers },
  });
  const body = await response.json();
  return { response, body };
}
