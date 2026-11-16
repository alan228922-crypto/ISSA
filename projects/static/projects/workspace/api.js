function csrfToken(documentRef = document) {
  const rendered = documentRef.querySelector?.('meta[name="csrf-token"]')?.content;
  if (rendered) return rendered;
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

export function postJson(url, payload, documentRef = document) {
  return requestJson(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }, documentRef);
}

export function urlFromTemplate(template, values) {
  return template.replace(/\{([^}]+)\}/g, (_, key) => encodeURIComponent(values[key]));
}
