// Ausfuehren in mongosh:
// mongosh "mongodb://localhost:27018/taxi_weather"

db.trips.countDocuments();

db.trips.aggregate([
  {
    $group: {
      _id: "$month",
      fahrten: { $sum: 1 }
    }
  },
  { $sort: { _id: 1 } }
]);

db.trips.aggregate([
  {
    $group: {
      _id: "$weather_condition",
      fahrten: { $sum: 1 },
      durchschnittlicheDauer: { $avg: "$duration_minutes" },
      durchschnittlicherFahrpreis: { $avg: "$fare_amount" },
      durchschnittlichesTrinkgeld: { $avg: "$tip_amount" }
    }
  },
  { $sort: { fahrten: -1 } }
]);

db.trips.aggregate([
  { $match: { month: "2025-07" } },
  {
    $group: {
      _id: {
        wetter: "$weather_condition",
        tageszeit: "$time_band"
      },
      fahrten: { $sum: 1 },
      durchschnittlicheStrecke: { $avg: "$distance_miles" }
    }
  },
  { $sort: { "_id.wetter": 1, fahrten: -1 } }
]);
