"use client";

interface Order {
  drinkType: string | null;
  size: string | null;
  milk: string | null;
  extras: string[];
  name: string | null;
}

export default function Receipt({ order }: { order: Order | null }) {
  if (!order) return null;

  return (
    <div className="w-full max-w-sm mx-auto bg-white rounded-xl shadow-lg border border-gray-300 p-6 mt-6">
      <div className="text-center mb-4">
        <h2 className="text-xl font-bold tracking-wide">🌙 MoonBrew Coffee</h2>
        <div className="border-b mt-2"></div>
      </div>

      <p className="text-gray-700 text-lg font-semibold mb-4">
        Order for <span className="font-bold">{order.name}</span>
      </p>

      <div className="space-y-2 text-gray-800">
        <p><strong>Drink:</strong> {order.size} {order.drinkType}</p>
        <p><strong>Milk:</strong> {order.milk}</p>

        <div>
          <strong>Extras:</strong>
          {order.extras.length === 0 ? (
            <p className="text-gray-500">None</p>
          ) : (
            <ul className="list-disc ml-6">
              {order.extras.map((ex, idx) => (
                <li key={idx}>{ex}</li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="border-t mt-4 pt-4 text-center text-gray-600 text-sm">
        Thank you for ordering ☕
      </div>
    </div>
  );
}
