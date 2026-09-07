"use client";

import { useEffect } from "react";

const ANTERIOR = /NetReto/g;

function sustituirNodoTexto(root: Node) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodos: Text[] = [];
  let actual: Node | null;
  while ((actual = walker.nextNode())) {
    if (actual.nodeValue?.includes("NetReto")) nodos.push(actual as Text);
  }
  for (const nodo of nodos) {
    nodo.nodeValue = nodo.nodeValue?.replace(ANTERIOR, "Tu Coach") ?? nodo.nodeValue;
  }
}

function sustituirAtributos(root: ParentNode) {
  root.querySelectorAll<HTMLElement>("[aria-label], [title]").forEach((elemento) => {
    for (const atributo of ["aria-label", "title"] as const) {
      const valor = elemento.getAttribute(atributo);
      if (valor?.includes("NetReto")) {
        elemento.setAttribute(atributo, valor.replace(ANTERIOR, "Tu Coach"));
      }
    }
  });
}

export default function BrandTextCleanup() {
  useEffect(() => {
    sustituirNodoTexto(document.body);
    sustituirAtributos(document.body);

    const observer = new MutationObserver((mutaciones) => {
      for (const mutacion of mutaciones) {
        for (const nodo of Array.from(mutacion.addedNodes)) {
          sustituirNodoTexto(nodo);
          if (nodo.nodeType === Node.ELEMENT_NODE) sustituirAtributos(nodo as ParentNode);
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  return null;
}
