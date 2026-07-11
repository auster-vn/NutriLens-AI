import { ProductDetailPanel } from "@/components/ProductDetailPanel";

export default async function ProductPage({ params }: { params: Promise<{ barcode: string }> }) {
  const { barcode } = await params;
  return <ProductDetailPanel barcode={barcode} />;
}
