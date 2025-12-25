import { useEffect, useState } from 'react';

interface Brand {
  id: number;
  name: string;
  logo_url: string;
}

export default function BrandsBackground() {
  const [brands, setBrands] = useState<Brand[]>([]);

  useEffect(() => {
    fetch('/api/backend/brands')
      .then(res => res.json())
      .then(data => {
        // Shuffle and take some
        const shuffled = data.sort(() => 0.5 - Math.random()).slice(0, 30);
        setBrands(shuffled);
      })
      .catch(err => console.error('Background fetch error:', err));
  }, []);

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden opacity-10 pointer-events-none">
      {brands.map((brand) => (
        <div
          key={brand.id}
          className="absolute transition-all duration-[10000ms] ease-linear"
          style={{
            top: `${Math.random() * 100}%`,
            left: `${Math.random() * 100}%`,
            transform: `scale(${0.5 + Math.random()}) rotate(${Math.random() * 360}deg)`,
          }}
        >
          {brand.logo_url ? (
            <img src={brand.logo_url} alt="" className="h-12 w-auto grayscale" />
          ) : (
            <span className="text-xl font-bold">{brand.name}</span>
          )}
        </div>
      ))}
    </div>
  );
}
