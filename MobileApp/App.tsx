import React, { useState } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createStackNavigator } from "@react-navigation/stack";
import HomeScreen from "./Screens/HomeScreen";
import CameraScreen from "./Screens/CameraScreen";
import AccountScreen from "./Screens/AccountScreen";
import LoginScreen from "./Screens/LoginScreen";
import RegisterScreen from "./Screens/SignUpScreen";
import SplashScreen from "./Screens/SplashScreen";
import RoleSelectScreen from "./Screens/RoleSelectScreen";
import PatientInfoScreen from "./Screens/PatientInfoScreen";
import DoctorInfoScreen from "./Screens/DoctorInfoScreen";

const Stack = createStackNavigator();

export default function App() {
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  if (isLoading) {
    return <SplashScreen onComplete={() => setIsLoading(false)} />;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen
          name="Login"
          options={{ headerShown: false }}
        >
          {(props) => <LoginScreen {...props} />}
        </Stack.Screen>

        <Stack.Screen
          name="Register"
          options={{ headerShown: false }}
        >
          {(props) => <RegisterScreen {...props} />}
        </Stack.Screen>

        <Stack.Screen
          name="Home"
          options={{ headerShown: false }}
        >
          {(props) => <HomeScreen {...props} setIsCameraActive={setIsCameraActive} />}
        </Stack.Screen>
        <Stack.Screen
          name="Camera"
          options={{ headerShown: false }}
        >
          {(props) => <CameraScreen {...props} setIsCameraActive={setIsCameraActive} />}
        </Stack.Screen>
        <Stack.Screen
          name="Account"
          options={{ headerShown: false }}
        >
          {(props) => <AccountScreen {...props} />}
        </Stack.Screen>
        <Stack.Screen
          name="RoleSelect"
          options={{ headerShown: false }}
        >
          {(props) => <RoleSelectScreen {...props} />}
        </Stack.Screen>
        <Stack.Screen
          name="PatientInfo"
          options={{ headerShown: false }}
        >
          {(props) => <PatientInfoScreen {...props} />}
        </Stack.Screen>
        <Stack.Screen
          name="DoctorInfo"
          options={{ headerShown: false }}
        >
          {(props) => <DoctorInfoScreen {...props} />}
        </Stack.Screen>
      </Stack.Navigator>
    </NavigationContainer>
  );
}