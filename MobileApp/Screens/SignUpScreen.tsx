import React, { useState } from "react";
import { StyleSheet, Text, View, TextInput, TouchableOpacity, KeyboardAvoidingView, Dimensions } from "react-native";

const screenHeight = Dimensions.get('window').height;
const screenWidth = Dimensions.get('window').width;

export default function SignUpScreen({ navigation }: { navigation: any }) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);

    async function signUpWithEmail() {
        // Implement sign up logic
        navigation.reset({
            index: 0,
            routes: [{ name: 'RoleSelect' }],
          });
    }

    async function goToLogin() {
        navigation.reset({
          index: 0,
          routes: [{ name: 'Login' }],
        });
      }

    return (
        <KeyboardAvoidingView behavior="padding" style={styles.container}>
            <View style={styles.innerContainer}>
                <Text style={styles.appTitle}>Blood Pleasure App</Text>
                <Text style={styles.headText}>Create Account !</Text>
                <View style={{ width: '100%', marginTop: 32, alignItems: 'center' }}>
                    <TextInput
                        value={email}
                        onChangeText={setEmail}
                        placeholder="Email Address"
                        style={styles.input}
                        autoCapitalize="none"
                    />
                    <View style={{ width: '100%', position: 'relative', alignItems: 'center' }}>
                        <TextInput
                            value={password}
                            onChangeText={setPassword}
                            placeholder="Password"
                            secureTextEntry={!showPassword}
                            style={styles.input}
                        />
                        <TouchableOpacity
                            style={styles.showPasswordBtn}
                            onPress={() => setShowPassword(!showPassword)}
                        >
                            <Text style={styles.showPasswordText}>Show Password</Text>
                        </TouchableOpacity>
                    </View>
                    <TextInput
                        value={confirmPassword}
                        onChangeText={setConfirmPassword}
                        placeholder="Confirm Password"
                        secureTextEntry={!showPassword}
                        style={styles.input}
                    />
                    <TouchableOpacity style={styles.button} onPress={signUpWithEmail} disabled={loading}>
                        <Text style={styles.buttonText}>Confirm</Text>
                    </TouchableOpacity>
                    <View style={styles.bottomRow}>
                        <Text style={styles.notMemberText}>Have an account?</Text>
                        <TouchableOpacity onPress={goToLogin}> 
                            <Text style={styles.loginText}>Login</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </View>
        </KeyboardAvoidingView>
    );
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
    headText: {
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
    showPasswordBtn: {
        position: 'absolute',
        right: 45,
        top: 32,
    },
    showPasswordText: {
        color: '#8f8e8e',
        fontSize: 14,
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
    loginText: {
        color: '#4662e6',
        fontWeight: 'bold',
        fontSize: 16,
        marginLeft: 8,
    },
});