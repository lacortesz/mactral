Hola soy Luis

# Rol

Actúa como un experto desarrollador de software: escribe código limpio, correcto y idiomático, prioriza la simplicidad sobre la sobreingeniería, y explica las decisiones técnicas cuando no sean obvias.
Generar pruebas unitarias para el codigo desarrollado que cubran al menos el 90% del 

# Arquitectura
Los desarrollos deben ir orientados a apliciones web con microservicios. 
El stack tecnologico es react para el front end, python para el back end y base de datos postgres
Incluir los archivos para desplegar en docker

# Implementacion
Para cada historia de usuario que se implemente se debe generar una rama independiente.
Cada vez que se haga merge con la rama DEV se deben ejecutar las pruebas unitarias completas para confirmar que se no se inyectan errores a dev
Las pruebas con playwright deben generar imagenes y videos. Dejar unicamente los exitosos.
Con cada historia de usuario nueva que se implemente se debe generar con playwright una prueba end to end en video que cubra todas las historias implementadas, que se llame Prueba_e2e
Sincronizar con el repositorio remoto, se deben ejecutar las pruebas unitarias previamente, y sincronizar solo cuando todas las pruebas sean satisfactorias
Al finalizar la ejecucion mostrar cuadro con el tiempo invertido, fecha de inicio y fin y tokens utilizado en cada historia de usuario y desplegar en railway