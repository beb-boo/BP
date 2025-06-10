import React, { useState } from "react";
import { StyleSheet, Text, View, TextInput, TouchableOpacity, Dimensions, KeyboardAvoidingView, Alert } from "react-native";
import { authApi } from '../api/auth';

const screenHeight = Dimensions.get('window').height;
const screenWidth = Dimensions.get('window').width;

export default function LoginScreen({ navigation, route }: { navigation: any; route: any }) {
    const [email, setEmail] = useState(route.params?.email || "");
    const [username, setUsername] = useState(route.params?.username || "");
    const [name, setName] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);

    const handleLogin = async () => {
        try {
            const response = await authApi.login({
                email: email,
                password: password
            });
            
            // Get user profile after successful login
            const userProfile = await authApi.getCurrentUser();
            
            // Navigate to home screen with user data
            navigation.reset({
                index: 0,
                routes: [{ 
                    name: 'Home',
                    params: { userData: userProfile }
                }],
            });
        } catch (error) {
            Alert.alert('Login Failed', 'Please check your credentials and try again.');
        }
    };

    return (
        <KeyboardAvoidingView behavior="padding" style={styles.container}>
            <View style={styles.innerContainer}>
                <Text style={styles.appTitle}>Blood Pleasure App</Text>
                <Text style={styles.welcomeText}>Welcome Back :3 !</Text>
                <View style={{ width: '100%', marginTop: 32, alignItems: 'center' }}>
                    <TextInput
                        value={email}
                        onChangeText={setEmail}
                        placeholder="Email Address"
                        style={styles.input}
                        autoCapitalize="none"
                    />
                    <TextInput
                        value={password}
                        onChangeText={setPassword}
                        placeholder="Password"
                        secureTextEntry
                        style={styles.input}
                    />
                    <TouchableOpacity onPress={() => {Alert.alert("Forgot Password?", "Forgot Password will be implemented here.");}}>
                        <Text style={styles.forgotText}>Forget Password ?</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
                        <Text style={styles.buttonText}>Login</Text>
                    </TouchableOpacity>
                    <View style={styles.bottomRow}>
                        <Text style={styles.notMemberText}>Not a member?</Text>
                        <TouchableOpacity onPress={() => navigation.navigate("Register")}> 
                            <Text style={styles.registerText}>Register</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </View>
        </KeyboardAvoidingView>
    )
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#fff",
        justifyContent: 'center',
        alignItems: 'center',
    },
    innerContainer: {
        width: '100%',
        alignItems: 'center',
        justifyContent: 'center',
        marginTop: 0,
    },
    appTitle: {
        fontSize: 22,
        fontWeight: '400',
        textAlign: 'center',
        marginBottom: 32,
        marginTop: 0,
    },
    welcomeText: {
        fontSize: 26,
        fontWeight: '600',
        textAlign: 'center',
        marginBottom: 32,
    },
    input: {
        backgroundColor: '#fff',
        borderColor: '#000',
        borderWidth: 1,
        borderRadius: 20,
        paddingHorizontal: 20,
        paddingVertical: 14,
        marginTop: 16,
        fontSize: 16,
        width: screenWidth * 0.8,
    },
    forgotText: {
        color: '#8f8e8e',
        fontSize: 14,
        textAlign: 'right',
        marginTop: 8,
        marginBottom: 8,
        marginRight: 8,
        alignSelf: 'flex-end',
    },
    button: {
        backgroundColor: '#4662e6',
        paddingVertical: 16,
        borderRadius: 20,
        marginTop: 24,
        width: screenWidth * 0.8,
        alignItems: 'center',
        justifyContent: 'center',
    },
    buttonText: {
        color: '#fff',
        fontWeight: 'bold',
        fontSize: 18,
    },
    bottomRow: {
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        marginTop: 32,
    },
    notMemberText: {
        color: '#8f8e8e',
        fontSize: 16,
        fontWeight: '500',
    },
    registerText: {
        color: '#4662e6',
        fontWeight: 'bold',
        fontSize: 16,
        marginLeft: 8,
    },
});
