import { Lato_400Regular, Lato_700Bold } from '@expo-google-fonts/lato';
import { Montserrat_800ExtraBold } from '@expo-google-fonts/montserrat';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

export default function Layout() {
  const [prontas] = useFonts({ Lato_400Regular, Lato_700Bold, Montserrat_800ExtraBold });
  if (!prontas) return null;
  return (
    <>
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false }} />
    </>
  );
}
