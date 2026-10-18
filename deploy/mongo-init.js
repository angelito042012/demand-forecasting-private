// Se ejecuta SOLO al inicializar un volumen vacio. Crea un usuario de aplicacion con readWrite
// sobre UNA base (equivalente al usuario minimo de Atlas). Las credenciales vienen del entorno.
const dbName = process.env.MONGO_APP_DB;
db.getSiblingDB(dbName).createUser({
  user: process.env.MONGO_APP_USER,
  pwd: process.env.MONGO_APP_PASSWORD,
  roles: [{ role: "readWrite", db: dbName }],
});
