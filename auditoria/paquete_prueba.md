# PAQUETE DE PRUEBA · solo para comprobar que el flujo W7 funciona (no es una auditoría del proyecto)

Versión: prueba-v1. Diseño ficticio y mínimo con fallos puestos a propósito, para ver que el auditor los detecta y que su
respuesta llega, se valida y se guarda.

## Proceso
Un sistema envía cada lunes una oferta a los clientes que llevan 60 días sin comprar.

## Nodos

### N1 · Elegir clientes y redactar la oferta (IA)
- Entrada: tabla de clientes. Salida: correo redactado.
- Dentro: elegir los clientes con más de 60 días sin compra y redactar un correo con un descuento del 20 %.
- Criterios: el correo es convincente.

### N2 · Enviar (automático)
- Entrada: correo redactado. Salida: correo enviado.
- Dentro: enviar el correo a todos los clientes elegidos, en cuanto N1 termina.
- Fuera: nada.
