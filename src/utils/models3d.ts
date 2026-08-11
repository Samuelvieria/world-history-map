import * as THREE from 'three';
import type { PositionedEvent } from './geo';
import { CATEGORIAS } from './categorias';

// Modelos 3D genéricos, construídos com geometria primitiva do Three.js — sem
// depender de baixar GLB de terceiros (evita ter que verificar licença de
// asset externo às pressas). Ver VISUAL.md, seção "Fontes de modelos 3D": um
// pacote GLB real (Kenney/Quaternius/Poly Pizza) continua um upgrade futuro
// válido, só não dá pra fazer isso sem checar a licença de cada arquivo.

function material(cor: string): THREE.Material {
  return new THREE.MeshStandardMaterial({ color: cor, metalness: 0.25, roughness: 0.65 });
}

function malha(geometria: THREE.BufferGeometry, cor: string, y = 0): THREE.Mesh {
  const m = new THREE.Mesh(geometria, material(cor));
  m.position.y = y;
  return m;
}

function umaEspada(cor: string): THREE.Object3D {
  const grupo = new THREE.Group();
  grupo.add(malha(new THREE.ConeGeometry(0.11, 0.26, 4), cor, 1.0));
  grupo.add(malha(new THREE.BoxGeometry(0.19, 0.78, 0.07), cor, 0.48));
  grupo.add(malha(new THREE.BoxGeometry(0.52, 0.12, 0.12), '#d1d5db', 0.07));
  grupo.add(malha(new THREE.CylinderGeometry(0.075, 0.075, 0.3, 8), '#3f3f46', -0.13));
  return grupo;
}

function espadasCruzadas(cor: string): THREE.Object3D {
  // Uma espada sozinha e' alta e fina (proporcao ~8:1): vista de angulo raso
  // vira um risco na tela — o mesmo defeito dos cilindros que foram tirados.
  // Duas espadas em X tem massa horizontal, entao lem como simbolo de qualquer
  // angulo. E' tambem o que o VISUAL.md pedia para esta categoria.
  const grupo = new THREE.Group();
  const inclinacao = Math.PI / 5;

  const esquerda = umaEspada(cor);
  esquerda.rotation.z = inclinacao;
  grupo.add(esquerda);

  const direita = umaEspada(cor);
  direita.rotation.z = -inclinacao;
  grupo.add(direita);

  // Leve giro do par inteiro para nunca ficar exatamente de perfil.
  grupo.rotation.y = Math.PI / 6;
  return grupo;
}

function predio(cor: string): THREE.Object3D {
  const grupo = new THREE.Group();
  grupo.add(malha(new THREE.BoxGeometry(0.85, 0.95, 0.85), cor, 0.48));
  const telhado = malha(new THREE.ConeGeometry(0.68, 0.5, 4), '#7c2d12', 1.2);
  telhado.rotation.y = Math.PI / 4;
  grupo.add(telhado);
  return grupo;
}

function piramide(cor: string): THREE.Object3D {
  const p = malha(new THREE.ConeGeometry(0.9, 1.05, 4), cor, 0.52);
  p.rotation.y = Math.PI / 4;
  return p;
}

function barco(cor: string): THREE.Object3D {
  const grupo = new THREE.Group();
  // Casco: cilindro deitado (eixo horizontal) — silhueta simples de casco que
  // lê bem de qualquer ângulo, sem depender de uma extrusão de forma custom.
  const casco = malha(new THREE.CylinderGeometry(0.22, 0.3, 1.3, 14), cor, 0.16);
  casco.rotation.z = Math.PI / 2;
  grupo.add(casco);
  grupo.add(malha(new THREE.CylinderGeometry(0.028, 0.028, 0.95, 6), '#78716c', 0.68));
  // Duas velas cruzadas em vez de uma só: de qualquer ângulo horizontal de
  // câmera pelo menos uma aparece com alguma largura, nunca some de perfil.
  const materialVela = new THREE.MeshStandardMaterial({ color: '#f5f5f4', side: THREE.DoubleSide });
  const vela1 = new THREE.Mesh(new THREE.PlaneGeometry(0.6, 0.55), materialVela);
  vela1.position.y = 0.78;
  grupo.add(vela1);
  const vela2 = vela1.clone();
  vela2.rotation.y = Math.PI / 2;
  grupo.add(vela2);
  return grupo;
}

function coroa(cor: string): THREE.Object3D {
  const grupo = new THREE.Group();
  grupo.add(malha(new THREE.CylinderGeometry(0.45, 0.5, 0.32, 12), cor, 0.2));
  const nPontas = 5;
  for (let i = 0; i < nPontas; i++) {
    const angulo = (i / nPontas) * Math.PI * 2;
    const ponta = malha(new THREE.ConeGeometry(0.1, 0.3, 6), cor, 0.52);
    ponta.position.x = Math.cos(angulo) * 0.38;
    ponta.position.z = Math.sin(angulo) * 0.38;
    grupo.add(ponta);
  }
  return grupo;
}

function pessoa(cor: string): THREE.Object3D {
  // Silhueta de figura togada (base larga, afunilando pros ombros) + cabeça
  // — como uma peça de xadrez, pra ficar inequivocamente uma "pessoa"
  // abstrata em qualquer ângulo de câmera, sem ambiguidade de forma.
  const grupo = new THREE.Group();
  grupo.add(malha(new THREE.ConeGeometry(0.42, 0.78, 16), cor, 0.39));
  grupo.add(malha(new THREE.CylinderGeometry(0.09, 0.11, 0.14, 10), cor, 0.85));
  grupo.add(malha(new THREE.SphereGeometry(0.2, 16, 16), '#eab308', 1.05));
  return grupo;
}

function livro(cor: string): THREE.Object3D {
  const grupo = new THREE.Group();
  grupo.add(malha(new THREE.BoxGeometry(0.85, 0.14, 0.65), cor, 0.1));
  grupo.add(malha(new THREE.BoxGeometry(0.87, 0.03, 0.67), '#f5f5f4', 0.19));
  return grupo;
}

function bussola(cor: string): THREE.Object3D {
  // Disco fino de lado quase some — precisa de espessura real pra ler bem
  // vista de perfil (ângulo comum de câmera neste app), não só de cima.
  const grupo = new THREE.Group();
  grupo.add(malha(new THREE.CylinderGeometry(0.38, 0.42, 0.22, 20), cor, 0.11));
  grupo.add(malha(new THREE.ConeGeometry(0.07, 0.5, 8), '#ef4444', 0.47));
  return grupo;
}

function marcadorSobrio(cor: string): THREE.Object3D {
  return malha(new THREE.SphereGeometry(0.32, 14, 14), cor, 0.32);
}

export function criarModeloParaEvento(evento: PositionedEvent): THREE.Object3D {
  const cor = CATEGORIAS[evento.categoria]?.cor ?? '#94a3b8';

  if (evento.modelo3D === 'piramide') return piramide(cor);
  if (evento.modelo3D === 'pessoa') return pessoa(cor);
  if (evento.modelo3D === 'barco') return barco(cor);

  switch (evento.categoria) {
    case 'batalha':
      return espadasCruzadas(cor);
    case 'construcao':
      return predio(cor);
    case 'naval':
      return barco(cor);
    case 'politico':
      return coroa(cor);
    case 'cultural':
      return livro(cor);
    case 'religioso':
      return predio(cor);
    case 'descoberta':
      return bussola(cor);
    case 'desastre':
      return marcadorSobrio(cor);
    default:
      return marcadorSobrio(cor);
  }
}
